import os
import subprocess

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers import fetch


def job_manager(service_name):
    hook_name = hookenv.hook_name()
    if hook_name in ('install', 'upgrade-charm'):
        manage_install()
    else:
        manage_services(service_name)


def manage_install():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(), 'files/bosh-templates-0.0.1.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def manage_services(service_name):
    pass
