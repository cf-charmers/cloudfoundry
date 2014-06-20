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

    def test_install_service_packages(self):
        pass

    def test_load_spec(self):
        pass

    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    @mock.patch('cloudfoundry.tasks.load_spec')
    @mock.patch('cloudfoundry.templating.RubyTemplateCallback')
    def test_job_templates(self, RubyTemplateCallback, load_spec, charm_dir):
        charm_dir.return_value = 'charm_dir'
        load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        expected_callbacks = RubyTemplateCallback.side_effect = [
            'callback1', 'callback2', 'callback3']
        actual_callbacks = tasks.job_templates('job_name')
        self.assertEqual(actual_callbacks, expected_callbacks)
        expected_calls = [
            mock.call('templates/src1', '/var/vcap/jobs/job_name/dest1', templates_dir='charm_dir/jobs'),
            mock.call('templates/src2', '/var/vcap/jobs/job_name/dest2', templates_dir='charm_dir/jobs'),
            mock.call('monit', '/etc/monit.d/job_name.cfg', templates_dir='charm_dir/jobs'),
        ]
        for expected_call in expected_calls:
            self.assertIn(expected_call, RubyTemplateCallback.call_args_list)
        self.assertEqual(RubyTemplateCallback.call_count, len(expected_calls))
        load_spec.assert_called_once_with('job_name')
