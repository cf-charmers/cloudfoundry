import os
import subprocess

from charmhelpers.core import hookenv
from charmhelpers import fetch


def install_bosh_template_renderer():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(), 'files/bosh-template-1.2611.0.pre.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def install_service_packages(service_name):
    pass
