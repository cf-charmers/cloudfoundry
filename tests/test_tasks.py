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
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_service_artifacts(self, OrchRelation, urlretrieve, taropen):
        OrchRelation.return_value = {'cf_release': 'version',
                                     'artifacts_url': 'http://url'}
        tgz = taropen.return_value.__enter__.return_value
        tasks.fetch_job_artifacts('job_name')
        urlretrieve.assert_called_once_with(
            'http://url/version/job_name.tgz',
            'charm_dir/jobs/version/job_name/job_name.tgz')
        taropen.assert_called_once_with(
            'charm_dir/jobs/version/job_name/job_name.tgz')
        tgz.extractall.assert_called_once_with(
            'charm_dir/jobs/version/job_name')

    def test_install_service_packages(self):
        pass

    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('cloudfoundry.tasks.yaml.safe_load')
    def test_load_spec(self, safe_load, mopen):
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
            mock.call('charm_dir/jobs/job1/spec'),
            mock.call('charm_dir/jobs/job2/spec'),
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

    @mock.patch('cloudfoundry.tasks.load_spec')
    def test_build_service_block(self, load_spec):
        load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        services = tasks.build_service_block('router_v1')
        self.assertEqual(services[0]['provided_data'][0],
                         contexts.RouterRelation)
        self.assertEqual(services[0]['required_data'][0],
                         contexts.NatsRelation)
        # Show that we converted to rubytemplatecallbacks
        self.assertIsInstance(services[0]['data_ready'][0],
                              templating.RubyTemplateCallback)
