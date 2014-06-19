import unittest
import mock

from cloudfoundry import jobs


class TestJobManager(unittest.TestCase):
    @mock.patch.object(jobs.hookenv, 'hook_name')
    @mock.patch.object(jobs, 'manage_services')
    @mock.patch.object(jobs, 'manage_install')
    def test_job_manager(self, manage_install, manage_services, hook_name):
        hook_name.return_value = 'install'
        jobs.job_manager('service1')
        hook_name.return_value = 'upgrade-charm'
        jobs.job_manager('service2')
        hook_name.return_value = 'foo-relation-joined'
        jobs.job_manager('service3')
        self.assertEqual(manage_install.call_count, 2)
        manage_services.assert_called_once_with('service3')

    @mock.patch('subprocess.check_call')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    @mock.patch('charmhelpers.fetch.filter_installed_packages')
    @mock.patch('charmhelpers.fetch.apt_install')
    def test_manage_install(self, apt_install, filter_installed_packages, charm_dir, check_call):
        filter_installed_packages.side_effect = lambda a: a
        charm_dir.return_value = 'charm_dir'
        jobs.manage_install()
        apt_install.assert_called_once_with(packages=['ruby'])
        check_call.assert_called_once_with(['gem', 'install', 'charm_dir/files/bosh-templates-0.0.1.gem'])

    def test_manage_services(self):
        pass
