#!/usr/bin/env python

import os
import yaml

from charmhelpers.core import hookenv
from charmhelpers.core import services

from charmgen.generator import CharmGenerator
from cloudfoundry.releases import RELEASES
from cloudfoundry.services import SERVICES
from cloudfoundry.contexts import JujuAPICredentials

from deployer.cli import setup_parser
from deployer.env.gui import GUIEnvironment
from deployer.action.importer import Importer
from deployer.deployment import Deployment


class JujuLoggingDeployment(Deployment):
    def _handle_feedback(self, feedback):
        for e in feedback.get_errors():
            hookenv.log(e, level=hookenv.ERROR)
        for e in feedback.get_warnings():
            hookenv.log(e, level=hookenv.WARNING)
        assert not feedback.has_errors, '\n'.join(feedback.get_errors())


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
    env = GUIEnvironment(creds['api_address'], creds['api_password'])
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
