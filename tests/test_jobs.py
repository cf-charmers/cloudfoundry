import unittest
import mock

from charmhelpers.core.services import ServiceManager
from cloudfoundry import contexts
from cloudfoundry import jobs
from cloudfoundry import tasks

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

    @mock.patch('cloudfoundry.contexts.CloudControllerRelation.get_credentials')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_build_service_block(self, relation_ids, mconfig, unit_get, log, get_creds):
        relation_ids.return_value = []
        unit_get.return_value = 'unit/0'
        services = jobs.build_service_block('router-v1')
        self.assertIsInstance(services[0]['provided_data'][0],
                              contexts.RouterRelation)
        self.assertIsInstance(services[0]['required_data'][0],
                              contexts.OrchestratorRelation)
        self.assertIsInstance(services[0]['required_data'][1],
                              contexts.NatsRelation)
        # Show that we converted to rubytemplatecallbacks
        self.assertIsInstance(services[0]['data_ready'][3],
                              tasks.JobTemplates)
        services = jobs.build_service_block('cloud-controller-v1')
        # Show that we include both default and additional handlers
        self.assertIsInstance(services[0]['data_ready'][3],
                              tasks.JobTemplates)
        self.assertEqual(services[0]['data_ready'][-1],
                         contexts.CloudControllerDBRelation.send_data)
