from charmhelpers.core import host

from charmhelpers.fetch import (
    apt_install, apt_update, add_source, filter_installed_packages
)


def prepare_cloudfoundry_environment(config_data, packages):
    add_source(config_data['source'], config_data.get('key'))
    apt_update(fatal=True)
    apt_install(packages=filter_installed_packages(packages), fatal=True)
    host.adduser('vcap')
