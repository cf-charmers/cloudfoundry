import logging
import threading

import tornado.ioloop
from tornado import gen

from cloudfoundry import actions
from config import (PENDING, COMPLETE, FAILED, RUNNING)
from cloudfoundry import utils


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
        return utils.get_env().status()

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
        result.append(actions.GenerateTactic())
        for service_name in adds:
            service = current['services'][service_name].copy()
            service['service_name'] = service_name
            branch = service.get('branch')
            if branch and branch.startswith('local:'):
                result.append(actions.UpdateCharmTactic(charm_url=branch))
            result.append(actions.DeployTactic(service=service))

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
                result.append(actions.AddRelation(
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
            env = utils.get_env()

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
