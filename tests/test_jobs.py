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
        self.assertEqual(manage_install.call_args_list, [
            mock.call('service1'),
            mock.call('service2'),
        ])
        self.assertEqual(manage_services.call_args_list, [
            mock.call('service3'),
        ])

    @mock.patch.object(jobs.tasks, 'install_bosh_template_renderer')
    def test_manage_install(self, install_btr):
        jobs.manage_install('service')
        install_btr.assert_called_once_with()

    def test_manage_services(self):
        pass
