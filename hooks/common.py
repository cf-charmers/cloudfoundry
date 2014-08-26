#!/usr/bin/env python

import os
import yaml
import shutil
import subprocess

from charmhelpers.core import hookenv
from charmhelpers.core import services

from charmgen.generator import CharmGenerator
from cloudfoundry.releases import RELEASES
from cloudfoundry.services import SERVICES
from cloudfoundry.contexts import JujuAPICredentials
from cloudfoundry.contexts import ArtifactsCache
from cloudfoundry.contexts import OrchestratorRelation
from cloudfoundry.path import path
from cloudfoundry.api import JujuLoggingDeployment
from cloudfoundry.api import APIEnvironment

from deployer.cli import setup_parser
from deployer.action.importer import Importer
from deployer.utils import setup_logging
from jujuclient import EnvError


def precache_job_artifacts(s):
    config = hookenv.config()
    version = config.get('cf_version')
    if not version or version == 'latest':
        version = RELEASES[0]['releases'][1]
    prefix = path('cf-{}'.format(version)) / 'amd64'
    base_url = path(config['artifacts_url']) / prefix
    base_path = path('/var/www') / prefix
    base_path.makedirs_p(mode=0755)
    for service in SERVICES.values():
        for job in service['jobs']:
            job_name = job['job_name']
            url = os.path.join(base_url, job_name)
            artifact = os.path.join(base_path, job_name)
            if not os.path.exists(artifact):
                subprocess.check_call(['wget', '-nv', url, '-O', artifact])


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
        env.expose('haproxy')
    finally:
        env.close()


def cache_unit_addresses(s):
    units = {}
    for rid in sorted(hookenv.relation_ids(OrchestratorRelation.name)):
        for unit in sorted(hookenv.related_units(rid)):
            units[unit] = hookenv.relation_get('private-address', unit, rid)
    cache_file = path(hookenv.charm_dir()) / 'unit_addresses'
    cache_file.write_text(yaml.safe_dump(units, default_flow_style=False))


def report_consolidated_health():
    cache_file = path(hookenv.charm_dir()) / 'unit_addresses'
    results = {
        'service': 'cloudfoundry',
        'health': 'pass',
        'state': hookenv.juju_status(),
        'units': {},
    }
    if cache_file.exists():
        units = yaml.safe_load(cache_file.text())
        for unit, address in units.iteritems():
            unit_dash = unit.replace('/', '-')
            output = subprocess.check_output([
                'ssh', 'root@{}'.format(address),
                '-i', path(hookenv.charm_dir()) / 'orchestrator-key',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'StrictHostKeyChecking=no',
                ' ; '.join([
                    'export CHARM_DIR=/var/lib/juju/agents/unit-{}/charm'.format(unit_dash),
                    'cd $CHARM_DIR',
                    'hooks/health',
                ]),
            ])
            results['units'][unit] = yaml.safe_load(output)
            health = results['units'][unit]['health']
            if health == 'fail':
                results['health'] = 'fail'
            elif health == 'warn' and results['health'] != 'fail':
                results['health'] = 'warn'
    print yaml.safe_dump(results, default_flow_style=False)


def manage():
    if hookenv.hook_name() == 'health':
        report_consolidated_health()
        return
    manager = services.ServiceManager([
        {
            'service': 'bundle',
            'required_data': [
                JujuAPICredentials(),
                ArtifactsCache(),
            ],
            'data_ready': [
                cache_unit_addresses,
                precache_job_artifacts,
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
