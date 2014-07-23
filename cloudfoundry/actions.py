import datetime
import logging
import os
import shutil

from cloudfoundry.config import (
    PENDING, COMPLETE, RUNNING, FAILED, STATES
    )

from deployer.charm import Charm
from deployer.service import Service
from deployer.utils import get_qualified_charm_url


from charmgen.generator import CharmGenerator
from cloudfoundry.releases import RELEASES
from cloudfoundry.services import SERVICES


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

    def _run(self, env,  **kwargs):
        version = kwargs.get('cf_release',  RELEASES[0]['releases'][1])
        build_dir = os.path.join(kwargs['repo'], str(version))
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
            charm_path = os.path.join(kwargs['repo'],
                                      str(version), series, charm_name)
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
                                   os.path.join(kwargs['repo'], str(version)),
                                   'trusty', s)
        env.deploy(svc.name,
                   # XXX version hack, have to probe for actual version after
                   # push
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


class AddRelationTactic(Tactic):
    name = "Add Relation"

    def _run(self, env, **kwargs):
        env.add_relation(kwargs['endpoint_a'], kwargs['endpoint_b'])


class RemoveRelationTactic(Tactic):
    name = "Add Relation"

    def _run(self, env, **kwargs):
        env.remove_relation(kwargs['endpoint_a'], kwargs['endpoint_b'])
