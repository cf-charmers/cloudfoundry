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
from cloudfoundry.contexts import ArtifactsCache
from cloudfoundry.contexts import OrchestratorRelation

from deployer.cli import setup_parser
from deployer.env.gui import GUIEnvironment
from deployer.utils import get_qualified_charm_url
from deployer.utils import parse_constraints
from deployer.action.importer import Importer
from deployer.deployment import Deployment
from deployer.utils import setup_logging
from jujuclient import EnvError


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
            archive = charm_file + '.zip'
            size = os.path.getsize(archive)
            with open(archive) as fp:
                self.client.add_local_charm(fp, series, size)
        else:
            self.client.add_charm(charm_url)
        self.client.deploy(
            name, charm_url, config=config, constraints=constraints,
            num_units=num_units, machine_spec=force_machine)

    def _get_units_in_error(self, status=None):
        """
        Ignore this unit when watching for errors, lest we are never
        able to get out of an error state with `resolved --retry`.
        """
        units = super(APIEnvironment, self)._get_units_in_error(status)
        local_unit = hookenv.local_unit()
        return [unit for unit in units if unit != local_unit]


def generate(s):
    config = hookenv.config()
    version = config.get('cf_version')
    if not version or version == 'latest':
        version = RELEASES[0]['releases'][1]
    build_dir = os.path.join(hookenv.charm_dir(), 'build', str(version))
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    generator = CharmGenerator(RELEASES, SERVICES)
    generator.select_release(version)
    generator.generate(build_dir)


def deploy(s):
    config = hookenv.config()
    version = config.get('cf_version')
    if not version or version == 'latest':
        version = RELEASES[0]['releases'][1]
    generator = CharmGenerator(RELEASES, SERVICES)
    generator.select_release(version)
    charm_dir = hookenv.charm_dir()
    build_dir = os.path.join(charm_dir, 'build', str(version))
    with open(os.path.join(build_dir, 'bundles.yaml')) as fp:
        bundle = yaml.load(fp)
    options = setup_parser().parse_args(['--series', 'trusty',
                                         '--local-mods',
                                         '--retry', '3'])
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
        try:
            importer.run()
        except Exception as e:
            hook_name = hookenv.hook_name()
            if hook_name.startswith('orchestrator-relation-'):
                hookenv.log('Error adding orchestrator relation: {}'.format(str(e)), hookenv.ERROR)
            else:
                raise
        # manually add the implicit relation between the orchestrator and
        # the generated charms; this can't be done in the bundle because
        # the orchestrator is not defined in the bundle
        orchestrator = hookenv.service_name()
        for service_name, service_data in bundle['cloudfoundry']['services'].items():
            # XXX: explicitly check if service has orchestrator interface
            if not service_data['charm'].startswith('cs:'):
                try:
                    env.add_relation(orchestrator, service_name)
                except EnvError as e:
                    if e.message.endswith('relation already exists'):
                        continue  # existing relations are ok, just skip
                    else:
                        hookenv.log('Error adding orchestrator relation: {}'.format(str(e)), hookenv.ERROR)
    finally:
        env.close()


def manage():
    manager = services.ServiceManager([
        {
            'service': 'bundle',
            'required_data': [
                JujuAPICredentials(),
                ArtifactsCache(),
            ],
            'data_ready': [
                generate,
                deploy,
            ],
            'start': [],
            'stop': [],
        },
        {
            'service': 'nginx',
            'required_data': [{'charm_dir': hookenv.charm_dir(),
                               'config': hookenv.config()}],
            'provided_data': [OrchestratorRelation()],
            'data_ready': [
                services.render_template(
                    source='nginx.conf',
                    target='/etc/nginx/sites-enabled/artifact_proxy'),
            ],
        },
    ])
    manager.manage()


if __name__ == '__main__':
    setup_logging(verbose=True, debug=True)

    manage()
