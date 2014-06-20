import unittest
import mock

from cloudfoundry import tasks


class TestTasks(unittest.TestCase):
    @mock.patch('subprocess.check_call')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    @mock.patch('charmhelpers.fetch.filter_installed_packages')
    @mock.patch('charmhelpers.fetch.apt_install')
    def test_install_bosh_template_renderer(self, apt_install, filter_installed_packages, charm_dir, check_call):
        filter_installed_packages.side_effect = lambda a: a
        charm_dir.return_value = 'charm_dir'
        tasks.install_bosh_template_renderer()
        apt_install.assert_called_once_with(packages=['ruby'])
        check_call.assert_called_once_with(['gem', 'install', 'charm_dir/files/bosh-template-1.2611.0.pre.gem'])
