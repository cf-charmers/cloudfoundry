import logging
import threading
import os

import tornado.ioloop
from tornado import gen

from cloudfoundry import actions
from config import (PENDING, COMPLETE, FAILED, RUNNING)
from cloudfoundry import utils

from jujuclient import Environment


class StateDatabase(object):
    def __init__(self, config):
        self.config = config
        self._env = None
        # expected is the state we are
        # transitioning to
        self.expected = {}
        # previous is the last (optional)
        # expected state
        self.previous = {}
        self.strategy = Strategy(self.env)
        self.history = []
        self.exec_lock = threading.Lock()

    def reset(self):
        self.expected = {}
        self._reset_strategy()

    def _reset_strategy(self):
        if self.strategy:
            self.history.append(self.strategy)
        self.strategy = Strategy(self.env)

    @property
    def env(self):
        if self._env:
            return self._env
        c = self.config
        self._env = self.get_env(
            c['juju.environment'],
            user=c['credentials.user'],
            password=c['credentials.password'])
        return self._env

    @property
    def real(self):
        return self.env.status()

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
        result.append(actions.GenerateTactic(
            repo=self.config['server.repository']))
        for service_name in adds:
            service = current['services'][service_name].copy()
            service['service_name'] = service_name
            branch = service.get('branch')
            if branch and branch.startswith('local:'):
                result.append(actions.UpdateCharmTactic(
                    charm_url=branch,
                    repo=self.config['server.repository']))
            result.append(actions.DeployTactic(service=service,
                                               repo=self.config['server.repository']))

        for service_name in deletes:
            result.push(actions.RemoveServiceTactic(service_name))

        logging.debug("Build New %s", result)
        return result

    def build_relations(self):
        current = self.expected
        result = []
        if not current:
            return result

        real = self.real
        # prev = self.previous

        crels = utils.flatten_relations(current['relations'])
        for rel in crels:
            if not utils.rel_exists(real, rel[0], rel[1]):
                result.append(actions.AddRelationTactic(
                    endpoint_a=rel[0], endpoint_b=rel[1]))

        # XXX skip deletes for now

        return result

    def execute_strategy(self):
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
                    self.execute_strategy)
            else:
                self._reset_strategy()
        finally:
            self.exec_lock.release()

    @classmethod
    def get_env(name=None, user=None, password=None):
        # A hook env will have this set
        api_addresses = os.environ.get('JUJU_API_ADDRESSES')
        if not api_addresses:
            # use the local option/connect which
            # parses local jenv info
            env = Environment.connect(name)
        else:
            env = Environment(api_addresses.split()[0])
            env.login(user=user, password=password)
        return env


class Strategy(list):
    def __init__(self, env):
        self.state = PENDING
        self.env = env

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
            env = self.env

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
