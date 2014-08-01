import logging
from functools import partial
from .path import path

from charmhelpers.core import hookenv
from charmhelpers.core import services

from cloudfoundry import contexts
from cloudfoundry import tasks
from cloudfoundry.services import SERVICES

PACKAGES_BASE_DIR = path('/var/vcap/packages')
RELEASES_DIR = path('/var/vcap/releases')


def job_manager(service_name):
    logging.basicConfig(level=logging.DEBUG)
    hook_name = hookenv.hook_name()
    if hook_name in ('install', 'upgrade-charm'):
        manage_install(service_name)
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
                tasks.fetch_job_artifacts,
                partial(tasks.install_job_packages,
                        PACKAGES_BASE_DIR, RELEASES_DIR),
                tasks.job_templates(job.get('mapping', {})),
                tasks.set_script_permissions,
                tasks.monit.svc_force_reload,
            ] + job.get('data_ready', []),
            'start': [tasks.monit.start, services.open_ports],
            'stop': [tasks.monit.stop, services.close_ports]
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
