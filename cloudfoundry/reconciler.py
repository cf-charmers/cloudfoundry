#!/usr/bin/env python

"""
Run deployer in a loop, then remove any services not
in the expected state.


ISSUES:
    local charm version in charm url
        need to probe server still
    reconcile loop adding same tactics more than once
        should only trigger builds after push/reality change
        execute should happen by queueing the callback
"""
import datetime
import json
import logging
import os
import signal
import shutil
import subprocess
import threading
import time

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.process
import tornado.web

from tornado import gen
from tornado.options import define, options
from jujuclient import Environment
from deployer.charm import Charm
from deployer.service import Service
from deployer.utils import get_qualified_charm_url

from charmgen.generator import CharmGenerator
from cloudfoundry.releases import RELEASES
from cloudfoundry.services import SERVICES

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3

PENDING = 0
RUNNING = 1
COMPLETE = 2
FAILED = -1

STATES = {
    PENDING: "PENDING",
    RUNNING: "RUNNING",
    COMPLETE: "COMPLETE",
    FAILED: "FAILED"
}

env_name = None
server = None
db = None


class StateDatabase(object):
    def __init__(self):
        # expected is the state we are
        # transitioning to
        self.expected = {}
        # previous is the last (optional)
        # expected state
        self.previous = {}
        self.strategy = Strategy()
        self.history = []
        self.exec_lock = threading.Lock()

    def reset(self):
        self.expected = {}
        self._reset_strategy()

    def _reset_strategy(self):
        if self.strategy:
            self.history.append(self.strategy)
        self.strategy = Strategy()

    @property
    def real(self):
        return get_env().status()

    def build_strategy(self, reality=None):
        if reality is None:
            reality = self.real
        if reality is None:
            return []

        # Service Deltas
        self.strategy.extend(self.build_services())
        self.strategy.extend(self.build_relations())

    def build_services(self):
        # This should do a 3-way merge from the previous expected state
        # to current with a delta for reality
        current = self.expected
        result = []
        if not current:
            return result

        real = self.real
        prev = self.previous
        # XXX This is a very shallow diff in the sense that it only does
        # service name merges and not charm revision
        # XXX This deals with bundle format and the juju-core status output
        # formats, so the key names are a little different
        adds = set(current['services'].keys()) - set(real['Services'].keys())
        deletes = set()
        if prev:
            deletes = set(prev['services'].keys()) - set(
                current['services'].keys()) & set(
                real['Services'].keys())

        # XXX detect when we really want to do this,
        # ie, hash has changed or something
        result.append(GenerateTactic())
        for service_name in adds:
            service = current['services'][service_name].copy()
            service['service_name'] = service_name
            branch = service.get('branch')
            if branch and branch.startswith('local:'):
                result.append(UpdateCharmTactic(charm_url=branch))
            result.append(DeployTactic(service=service))

        for service_name in deletes:
            result.push(RemoveServiceTactic(service_name))

        logging.debug("Build New %s", result)
        return result

    def build_relations(self):
        current = self.expected
        result = []
        if not current:
            return result

        real = self.real
        prev = self.previous

        def flatten_relations(rels):
            result = []
            for pair in rels:
                a = pair[0]
                b = pair[1]
                if isinstance(b, list):
                    for ep in b:
                        result.append((a, ep))
                else:
                    result.append(tuple(sorted((a, b))))
            return set(result)

        def flatten_reality(real):
            result = set()
            for s, d in real['Services'].items():
                rels = d .get('Relations', {})
                for iface, reps in rels.items():
                    for rep in reps:
                        result.add(tuple(
                            sorted(('%s:%s' % (s, iface), rep))))
            return result


        def _rel_exists(reality, end_a, end_b):
            # Checks for a named relation on one side that matches the local
            # endpoint and remote service.
            (name_a, name_b, rem_a, rem_b) = (end_a, end_b, None, None)

            if ":" in end_a:
                name_a, rem_a = end_a.split(":", 1)
            if ":" in end_b:
                name_b, rem_b = end_b.split(":", 1)

            try:
                rels_svc_a = reality['Services'][name_a].get('Relations', {})

                found = False
                for r, related in rels_svc_a.items():
                    if name_b in related:
                        if rem_a and r not in rem_a:
                            continue
                        found = True
                        break
                if found:
                    return True
            except KeyError:
                pass
            return False

        crels = flatten_relations(current['relations'])
        for rel in crels:
            if not _rel_exists(real, rel[0], rel[1]):
                result.append(AddRelation(
                    endpoint_a=rel[0], endpoint_b=rel[1]))

        # XXX skip deletes for now

        return result

    def execute_strategy(self, env):
        # each strategy is a list of tactics,
        # we track the state of each of those
        # by mutating the tactic in the list
        # execute strategy shouldn't blocka
        # so if the lock is taken we continue
        # without modifying the strategy
        # and pick up in the next timeout cycle
        if not self.strategy.runnable:
            return

        if not self.exec_lock.acquire(False):
            return
        try:
            logging.debug("Exec Strat %s", self.strategy)
            self.strategy()
            if self.strategy.runnable:
                tornado.ioloop.IOLoop.instance().add_callback(
                    self.execute_strategy, env)
            else:
                self._reset_strategy()
        finally:
            self.exec_lock.release()


class Strategy(list):
    def __init__(self):
        self.state = PENDING

    def find_next_tactic(self):
        if not self:
            return None
        for tactic in self:
            if tactic.state == PENDING:
                return tactic
        return None

    @property
    def runnable(self):
        if not self:
            return False
        found = False
        for tactic in self:
            if tactic.state == COMPLETE:
                continue
            if tactic.state != PENDING:
                return False
            else:
                found = True
        return found

    @gen.coroutine
    def __call__(self, env=None):
        if env is None:
            env = get_env()

        current = self.find_next_tactic()
        if not current:
            self.state = COMPLETE
        else:
            self.state = RUNNING
            current.run(env)
            if current.state != COMPLETE:
                self.state = FAILED

    def __str__(self):
        return "Strategy %s" % [str(t) for t in self]


class Tactic(object):
    def __init__(self,  **kwargs):
        self.state = PENDING
        self.failure = None
        self.start_time = None
        self.end_time = None
        self.kwargs = kwargs

    def __str__(self):
        return "%s [%s]: %s" % (self.name, STATES[self.state], self.kwargs)

    def run(self, env):
        if self.state != PENDING:
            raise ValueError("strategy out of order")
        self.start_time = datetime.datetime.now()
        self.state = RUNNING
        try:
            logging.debug("Running %s", self)
            self._run(env, **self.kwargs)
            self.state = COMPLETE
        except Exception, e:
            logging.debug("Tactic Failed", exc_info=True)
            self.state = FAILED
            self.failure = e
        finally:
            self.end_time = datetime.datetime.now()


class GenerateTactic(Tactic):
    name = "Generate charms"

    def _run(self, env, **kwargs):
        version = kwargs.get('cf_release',  RELEASES[0]['releases'][1])
        build_dir = os.path.join(options.repo, str(version))
        if os.path.exists(build_dir):
            return
        generator = CharmGenerator(RELEASES, SERVICES)
        generator.select_release(version)
        generator.generate(build_dir)


class UpdateCharmTactic(Tactic):
    name = "Update charm"

    def _run(self, env, **kwargs):
        charm_url = get_qualified_charm_url(kwargs['charm_url'])
        if charm_url.startswith('local:'):
            series, charm_id = charm_url.split(':')[1].split('/')
            charm_name = charm_id.rsplit('-', 1)[0]
            charm_file = os.path.join('/tmp', charm_id)
            version = kwargs.get('cf_release',  RELEASES[0]['releases'][1])
            charm_path = os.path.join(options.repo, str(version), series, charm_name)
            shutil.make_archive(charm_file, 'zip', charm_path)
            archive = charm_file + '.zip'
            size = os.path.getsize(archive)
            with open(archive) as fp:
                env.add_local_charm(fp, series, size)


class DeployTactic(Tactic):
    name = "Deploy"

    def _run(self, env, **kwargs):
        s = kwargs['service']
        svc = Service(s['service_name'], s)
        version = kwargs.get('cf_release',  RELEASES[0]['releases'][1])
        charm = Charm.from_service(s['service_name'],
                                   os.path.join(options.repo, str(version)),
                                   'trusty', s)
        env.deploy(svc.name,
                   # XXX version hack, have to probe for actual version after push
                   charm.charm_url + "-0",
                   config=svc.config,
                   constraints=svc.constraints,
                   num_units=svc.num_units)
        if svc.expose:
            env.expose(svc.name)


class RemoveServiceTactic(Tactic):
    name = "Remove Service"

    def _run(self, env, **kwargs):
        env.destroy_service(kwargs['service_name'])


class AddRelation(Tactic):
    name = "Add Relation"

    def _run(self, env, **kwargs):
        env.add_relation(kwargs['endpoint_a'], kwargs['endpoint_b'])


class RemoveRelation(Tactic):
    name = "Add Relation"

    def _run(self, env, **kwargs):
        env.remove_relation(kwargs['endpoint_a'], kwargs['endpoint_b'])


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


def get_env(name=None, user="user-admin", password=None):
    # A hook env will have this set
    api_addresses = os.environ.get('JUJU_API_ADDRESSES')
    if not api_addresses:
        # use the local option/connect which
        # parses local jenv info
        env = Environment.connect(name or options.env_name)
    else:
        env = Environment(api_addresses.split()[0])
        env.login(user=user,
                  password=password or options.password)
    return env


def reconcile():
    # delta state real vs expected
    # build strategy
    # execute strategy inside lock
    env = get_env()
    if not db.strategy:
        reality = db.real
        db.build_strategy(reality)
    if db.strategy:
        db.execute_strategy(env)


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
                 MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
    io_loop = tornado.ioloop.IOLoop.instance()

    deadline = time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN

    def stop_loop():
        now = time.time()
        if now < deadline and (io_loop._callbacks or io_loop._timeouts):
            io_loop.add_timeout(now + 1, stop_loop)
        else:
            io_loop.stop()
            logging.info('Shutdown')
    stop_loop()


def record_pid():
    pid_dir = os.path.expanduser('~/.config/juju-deployer')
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    with open(os.path.join(pid_dir, 'server.pid'), 'w') as fp:
        fp.write('%s\n' % os.getpid())


def current_env():
    return subprocess.check_output(['juju', 'switch']).strip()


def main():
    define("port", default=8888, help="run on the given port", type=int)
    define("env_name", default=current_env(), help="env to manage", type=str)
    define("repo", default=os.getcwd(), help="local charm repo", type=str)
    define("user", default="user-admin", help="connect to env as", type=str)
    define("password", help="password to connect to env with", type=str)

    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/api/v1/", StateHandler),
        (r"/api/v1/strategy", StrategyHandler),
        (r"/api/v1/reset", ResetHandler),
    ],
        autoreload=True)

    global server
    global db

    if not os.path.exists(options.repo):
        os.makedirs(options.repo)

    db = StateDatabase()
    server = tornado.httpserver.HTTPServer(application)
    server.listen(options.port)

    signal.signal(signal.SIGTERM, sig_restart)
    signal.signal(signal.SIGINT, sig_restart)
    signal.signal(signal.SIGHUP, sig_reconcile)
    record_pid()
    loop = tornado.ioloop.IOLoop.instance()
    # tornado.ioloop.PeriodicCallback(reconcile, 500, io_loop=loop).start()
    loop.start()


if __name__ == "__main__":
    main()
