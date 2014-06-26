import unittest
import mock

from cloudfoundry import contexts
from cloudfoundry import tasks
from cloudfoundry import templating


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.charm_dir_patch = mock.patch(
            'charmhelpers.core.hookenv.charm_dir')
        self.charm_dir = self.charm_dir_patch.start()
        self.charm_dir.return_value = 'charm_dir'

    def tearDown(self):
        self.charm_dir_patch.stop()

    @mock.patch('subprocess.check_call')
    @mock.patch('charmhelpers.fetch.filter_installed_packages')
    @mock.patch('charmhelpers.fetch.apt_install')
    def test_install_bosh_template_renderer(self, apt_install,
                                            filter_installed_packages,
                                            check_call):
        filter_installed_packages.side_effect = lambda a: a
        tasks.install_bosh_template_renderer()
        apt_install.assert_called_once_with(packages=['ruby'])
        check_call.assert_called_once_with(['gem', 'install',
                                            'charm_dir/files/' +
                                            'bosh-template-1.2611.0.pre.gem'])

    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts(self, OrchRelation, get_job_path, urlretrieve, taropen):
        OrchRelation.return_value = {'cf_release': 'version',
                                     'artifacts_url': 'http://url'}
        get_job_path.return_value = 'job_path'
        tgz = taropen.return_value.__enter__.return_value
        tasks.fetch_job_artifacts('job_name')
        urlretrieve.assert_called_once_with(
            'http://url/version/job_name.tgz',
            'job_path/job_name.tgz')
        taropen.assert_called_once_with('job_path/job_name.tgz')
        tgz.extractall.assert_called_once_with('job_path')

    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_same_version(self, OrchRelation, get_job_path, exists, urlretrieve, taropen):
        OrchRelation.return_value = {'cf_release': 'version', 'artifacts_url': 'http://url'}
        get_job_path.return_value = 'job_path'
        exists.return_value = True
        tasks.fetch_job_artifacts('job_name')
        assert not urlretrieve.called
        assert not taropen.called

    @mock.patch('os.symlink')
    @mock.patch('os.unlink')
    @mock.patch('shutil.copytree')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_install_job_packages(self, OrchRelation, get_job_path, exists, copytree, unlink, symlink):
        get_job_path.return_value = 'job_path'
        OrchRelation.return_value = {'cf_release': 'version'}
        exists.return_value = False
        tasks.install_job_packages('job_name')
        exists.assert_called_once_with('/var/vcap/packages/version/job_name')
        copytree.assert_called_once_with(
            'job_path/packages', '/var/vcap/packages/version/job_name')
        unlink.assert_called_once_with('/var/vcap/packages/job_name')
        symlink.assert_called_once_with('/var/vcap/packages/version/job_name', '/var/vcap/packages/job_name')

    @mock.patch('os.symlink')
    @mock.patch('os.unlink')
    @mock.patch('shutil.copytree')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_install_job_packages_same_version(self, OrchRelation, get_job_path, exists, copytree, unlink, symlink):
        get_job_path.return_value = 'job_path'
        OrchRelation.return_value = {'cf_release': 'version'}
        exists.return_value = True
        tasks.install_job_packages('job_name')
        exists.assert_called_once_with('/var/vcap/packages/version/job_name')
        assert not copytree.called
        assert not unlink.called
        assert not symlink.called

    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_get_job_path(self, OrchRelation):
        OrchRelation.return_value = {'cf_release': 'version'}
        self.assertEqual(tasks.get_job_path('job_name'), 'charm_dir/jobs/version/job_name')

    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('cloudfoundry.tasks.yaml.safe_load')
    def test_load_spec(self, safe_load, mopen, get_job_path):
        get_job_path.side_effect = ['job_path1', 'job_path2']
        safe_load.side_effect = [
            {'p1': 'v1'},
            {'p2': 'v2'},
        ]
        self.assertEquals(tasks.load_spec('job1'), {'p1': 'v1'})
        self.assertEquals(tasks.load_spec('job1'), {'p1': 'v1'})
        self.assertEqual(mopen.call_count, 1)
        self.assertEqual(safe_load.call_count, 1)
        self.assertEquals(tasks.load_spec('job2'), {'p2': 'v2'})
        self.assertEqual(mopen.call_count, 2)
        self.assertEqual(safe_load.call_count, 2)
        self.assertEqual(mopen.call_args_list, [
            mock.call('job_path1/spec'),
            mock.call('job_path2/spec'),
        ])

    @mock.patch('cloudfoundry.tasks.load_spec')
    @mock.patch('cloudfoundry.templating.RubyTemplateCallback')
    def test_job_templates(self, RubyTemplateCallback, load_spec):
        load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        expected_callbacks = RubyTemplateCallback.side_effect = [
            'callback1', 'callback2', 'callback3']
        actual_callbacks = tasks.job_templates('job_name')
        self.assertEqual(actual_callbacks, expected_callbacks)
        expected_calls = [
            mock.call('templates/src1', '/var/vcap/jobs/job_name/dest1',
                      templates_dir='charm_dir/jobs'),
            mock.call('templates/src2', '/var/vcap/jobs/job_name/dest2',
                      templates_dir='charm_dir/jobs'),
            mock.call('monit', '/etc/monit.d/job_name.cfg',
                      templates_dir='charm_dir/jobs'),
        ]
        for expected_call in expected_calls:
            self.assertIn(expected_call, RubyTemplateCallback.call_args_list)
        self.assertEqual(RubyTemplateCallback.call_count, len(expected_calls))
        load_spec.assert_called_once_with('job_name')

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch('cloudfoundry.tasks.load_spec')
    def test_build_service_block(self, load_spec, relation_ids):
        load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        relation_ids.return_value = []
        services = tasks.build_service_block('router_v1')
        self.assertIsInstance(services[0]['provided_data'][0],
                              contexts.RouterRelation)
        self.assertIsInstance(services[0]['required_data'][0],
                              contexts.OrchestratorRelation)
        self.assertIsInstance(services[0]['required_data'][1],
                              contexts.NatsRelation)
        # Show that we converted to rubytemplatecallbacks
        self.assertIsInstance(services[0]['data_ready'][2],
                              templating.RubyTemplateCallback)
