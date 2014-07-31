import unittest
import mock

from charmhelpers.core.services import ServiceManager
from cloudfoundry import jobs

from release1 import SERVICES


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


    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch.object(jobs.tasks, 'install')
    @mock.patch.object(jobs.tasks, 'install_base_dependencies')
    def test_manage_install(self, install_base, install, relation_ids):
        jobs.manage_install('cloud_controller_v1', SERVICES)
        install_base.assert_called_once_with()
        install.assert_called_once(SERVICES['cloud_controller_v1'])

    @mock.patch('charmhelpers.core.hookenv.log', mock.Mock())
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch.object(ServiceManager, 'manage')
    @mock.patch('cloudfoundry.tasks.load_spec')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    def test_manage_services(self, charm_dir, load_spec, manage, relation_ids):
        # XXX: This test is currently very weak, we don't assert
        # the emit quality, but the units below it are better
        # tested
        charm_dir.return_value = 'charm_dir'
        load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        relation_ids.return_value = []
        jobs.manage_services('cloud_controller_v1', SERVICES)
        manage.assert_called_once_with()
