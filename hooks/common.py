#!/usr/bin/env python

import os
import yaml
import shutil

from charmhelpers.core import hookenv
from charmhelpers.core import services

from charmgen.generator import CharmGenerator
from cloudfoundry.releases import RELEASES
from cloudfoundry.services import SERVICES
from cloudfoundry.contexts import JujuAPICredentials

from deployer.cli import setup_parser
from deployer.env.gui import GUIEnvironment
from deployer.utils import get_qualified_charm_url
from deployer.utils import parse_constraints
from deployer.action.importer import Importer
from deployer.deployment import Deployment


class JujuLoggingDeployment(Deployment):
    def _handle_feedback(self, feedback):
        for e in feedback.get_errors():
            hookenv.log(e, level=hookenv.ERROR)
        for e in feedback.get_warnings():
            hookenv.log(e, level=hookenv.WARNING)
        assert not feedback.has_errors, '\n'.join(feedback.get_errors())


class APIEnvironment(GUIEnvironment):
    """
    Environment subclass that uses the APi but supports local charms.
    """
    def deploy(self, name, charm_url, repo=None, config=None, constraints=None,
               num_units=1, force_machine=None):
        charm_url = get_qualified_charm_url(charm_url)
        constraints = parse_constraints(constraints)
        if charm_url.startswith('local:'):
            series, charm_id = charm_url.split(':')[1].split('/')
            charm_name = charm_id.rsplit('-', 1)[0]
            charm_file = os.path.join('/tmp', charm_id)
            charm_path = os.path.join(repo, series, charm_name)
            shutil.make_archive(charm_file, 'zip', charm_path)
            with open(charm_file + '.zip') as fp:
                fp.seek(0, 2)
                size = fp.tell()
                fp.seek(0)
                self.client.add_local_charm(fp, series, size)
        else:
            self.client.add_charm(charm_url)
        self.client.deploy(
            name, charm_url, config=config, constraints=constraints,
            num_units=num_units, machine_spec=force_machine)


def generate(s):
    version = hookenv.config('cf_release') or RELEASES[0]['releases'][1]
    build_dir = os.path.join(hookenv.charm_dir(), 'build', str(version))
    if os.path.exists(build_dir):
        return  # TODO: Handle re-run using upgrade-charm
    generator = CharmGenerator(RELEASES, SERVICES)
    generator.select_release(version)
    generator.generate(build_dir)


def deploy(s):
    version = hookenv.config('cf_release') or RELEASES[0]['releases'][1]
    generator = CharmGenerator(RELEASES, SERVICES)
    generator.select_release(version)
    charm_dir = hookenv.charm_dir()
    build_dir = os.path.join(charm_dir, 'build', str(version))
    with open(os.path.join(build_dir, 'bundles.yaml')) as fp:
        bundle = yaml.load(fp)
    options = setup_parser().parse_args(['--series', 'trusty', '--local-mods'])
    creds = JujuAPICredentials()
    env = APIEnvironment(creds['api_address'], creds['api_password'])
    deployment = JujuLoggingDeployment(
        name='cloudfoundry',
        data=bundle['cloudfoundry'],
        include_dirs=[],
        repo_path=build_dir)
    importer = Importer(env, deployment, options)
    env.connect()
    juju_home = os.environ['JUJU_HOME'] = os.path.join(charm_dir, '.juju')
    if not os.path.exists(juju_home):
        os.mkdir(juju_home)
    try:
        importer.run()
    finally:
        env.close()


def manage():
    manager = services.ServiceManager([
        {
            'service': 'bundle',
            'required_data': [JujuAPICredentials()],
            'data_ready': [
                generate,
                deploy,
            ],
            'start': [],
            'stop': [],
        },
    ])
    manager.manage()


if __name__ == '__main__':
    manage()
