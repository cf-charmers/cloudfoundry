from charmhelpers.core import hookenv
from charmhelpers.core import services

from cloudfoundry import tasks
from cloudfoundry.services import SERVICES


def job_manager(service_name):
    hook_name = hookenv.hook_name()
    if hook_name in ('install', 'upgrade-charm'):
        manage_install(service_name)
    else:
        manage_services(service_name)


def manage_install(service_name):
    tasks.install_base_dependencies()


def manage_services(service_name, service_data=SERVICES):
    service_def = tasks.build_service_block(service_name, service_data)
    services.ServiceManager(service_def).manage()
