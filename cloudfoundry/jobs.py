from charmhelpers.core import hookenv
from cloudfoundry import tasks


def job_manager(service_name):
    hook_name = hookenv.hook_name()
    if hook_name in ('install', 'upgrade-charm'):
        manage_install(service_name)
    else:
        manage_services(service_name)


def manage_install(service_name):
    tasks.install_bosh_template_renderer()


def manage_services(service_name):
    pass
