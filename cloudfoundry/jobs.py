import logging
from functools import partial
from .path import path
import yaml

from charmhelpers.core import hookenv
from charmhelpers.core import services

from cloudfoundry import contexts
from cloudfoundry import tasks
from cloudfoundry import health_checks
from cloudfoundry.services import SERVICES

PACKAGES_BASE_DIR = path('/var/vcap/packages')
RELEASES_DIR = path('/var/vcap/releases')


def job_manager(service_name):
    logging.basicConfig(level=logging.DEBUG)
    hook_name = hookenv.hook_name()
    if hook_name in ('install', 'upgrade-charm'):
        manage_install(service_name)
    elif hook_name == 'health':
        report_health(service_name)
    else:
        manage_services(service_name)


def build_service_block(charm_name, service_defs=SERVICES):
    service_def = service_defs[charm_name]
    result = []
    for job in service_def.get('jobs', []):
        job_def = {
            'service': job['job_name'],
            'ports': job.get('ports', []),
            'required_data': [contexts.OrchestratorRelation()] +
                             [r() for r in job.get('required_data', [])],
            'provided_data': [p() for p in job.get('provided_data', [])],
            'data_ready': [
                tasks.install_orchestrator_key,
                tasks.fetch_job_artifacts,
                partial(tasks.install_job_packages,
                        PACKAGES_BASE_DIR, RELEASES_DIR),
                tasks.job_templates(job.get('mapping', {})),
                tasks.set_script_permissions,
                tasks.monit.svc_force_reload,
            ] + job.get('data_ready', []),
            'start': [tasks.monit.start, services.open_ports],
            'stop': [tasks.monit.stop, services.close_ports],
        }
        result.append(job_def)
    return result


def manage_install(service_name, service_data=SERVICES):
    tasks.install_base_dependencies()
    service_def = service_data[service_name]
    tasks.install(service_def)


def manage_services(service_name, service_data=SERVICES):
    service_def = build_service_block(service_name, service_data)
    services.ServiceManager(service_def).manage()


def report_health(charm_name, service_data=SERVICES):
    service_def = service_data[charm_name]
    results = []
    health = 'pass'
    checks = service_def.get('health', []) + [health_checks.monit_summary]
    for health_check in checks:
        result = health_check(service_def)
        if result['health'] == 'fail':
            health = 'fail'
        elif result['health'] == 'warn' and health != 'fail':
            health = 'warn'
        results.append(result)
    print yaml.safe_dump({
        'service': charm_name,
        'health': health,
        'state': hookenv.juju_status(),
        'checks': results,
    }, default_flow_style=False)
