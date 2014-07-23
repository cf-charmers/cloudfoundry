#!/usr/bin/env python

"""
Run deployer in a loop, then remove any services not
in the expected state.

To experiment with this::

    #activate virtualenv
    . .tox/py27/bin/activate
    python cloudfoundry/reconciler.py \
        --logging=debug --repo=build --port=8888

    # then in another window you can do the follow to play
    # with the REST API
    cd tests
    ./test-server.sh

    This should push a bundle of expected state, HUP the
    server to force a run and then status the system.
    Debug output should show whats happening and


ISSUES:
    local charm version in charm url
        need to probe server still
    reconcile loop:
        should only trigger builds after push/reality change
        execute should happen by queueing the callback
        should listen directly on the websocket and schedule
            rebuilds on change
    no support for unit state currently (auto-retry/replace, etc)
    relation removal still needs work
"""
import json
import logging
import os
import signal
import time

import tornado.autoreload
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.process
import tornado.web

from tornado.options import define, options
from cloudfoundry import config
from cloudfoundry import model
from cloudfoundry import utils

env_name = None
server = None
db = None


def reconcile():
    # delta state real vs expected
    # build strategy
    # execute strategy inside lock
    if not db.strategy:
        reality = db.real
        db.build_strategy(reality)
    if db.strategy:
        db.execute_strategy()


def sig_reconcile(sig, frame):
    logging.info("Forcing reconcile loop")
    tornado.ioloop.IOLoop.instance().add_callback(reconcile)


def sig_restart(sig, frame):
    logging.warning('Caught signal: %s', sig)
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)


def shutdown():
    logging.info('Stopping http server')
    server.stop()

    logging.info('Will shutdown in %s seconds ...',
                 config.MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
    io_loop = tornado.ioloop.IOLoop.instance()

    deadline = time.time() + config.MAX_WAIT_SECONDS_BEFORE_SHUTDOWN

    def stop_loop():
        now = time.time()
        if now < deadline and (io_loop._callbacks or io_loop._timeouts):
            io_loop.add_timeout(now + 1, stop_loop)
        else:
            io_loop.stop()
            logging.info('Shutdown')
    stop_loop()


class StateHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(json.dumps(db.expected, indent=2))

    def post(self):
        db.expected = json.loads(self.request.body)
        tornado.ioloop.IOLoop.instance().add_callback(reconcile)


class StrategyHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(json.dumps([str(t) for t in db.strategy],
                              indent=2))


class ResetHandler(tornado.web.RequestHandler):
    def get(self):
        db.reset()


def main():
    define('config', default='/etc/juju-deployer/server.conf', type=str)

    tornado.options.parse_command_line()
    config = utils.parse_config(options.config, {
        'server.address': '127.0.0.1',
        'server.port': 8888,
        'credentials.user': 'user-admin',
        'server.repository': 'build',
        'juju.environment': utils.current_env()
    })

    application = tornado.web.Application([
        (r"/api/v1/", StateHandler),
        (r"/api/v1/strategy", StrategyHandler),
        (r"/api/v1/reset", ResetHandler),
    ],
        autoreload=True,
        config=config,
        **config['server']
    )

    global server
    global db

    if not os.path.exists(config['server.repository']):
        os.makedirs(config['server.repository'])

    db = model.StateDatabase(config)
    server = tornado.httpserver.HTTPServer(application)
    server.listen(config['server.port'], config['server.address'])

    signal.signal(signal.SIGTERM, sig_restart)
    signal.signal(signal.SIGINT, sig_restart)
    signal.signal(signal.SIGHUP, sig_reconcile)

    # config file change should reload the application
    # its values are passed to Application init
    tornado.autoreload.watch(options.config)
    utils.record_pid()
    loop = tornado.ioloop.IOLoop.instance()
    # tornado.ioloop.PeriodicCallback(reconcile, 500, io_loop=loop).start()
    loop.start()


if __name__ == "__main__":
    main()
