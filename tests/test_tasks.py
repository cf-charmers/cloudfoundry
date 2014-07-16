import unittest
import mock
import urllib

from charmhelpers.core import services
from cloudfoundry import contexts
from cloudfoundry import tasks


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

    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts(self, OrchRelation, get_job_path, urlretrieve,
                                 taropen, mkdir, mopen, md5, log, remove):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        urlretrieve.return_value = (None, {'ETag': '"deadbeef"'})
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        tgz = taropen.return_value.__enter__.return_value
        tasks.fetch_job_artifacts('job_name')
        urlretrieve.assert_called_once_with(
            'http://url/cf-version/amd64/job_name',
            'job_path/job_name.tgz')
        md5.assert_called_once_with('read')
        taropen.assert_called_once_with('job_path/job_name.tgz')
        tgz.extractall.assert_called_once_with('job_path')

    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_missing_checksum(
            self, OrchRelation, get_job_path, urlretrieve,
            taropen, mkdir, mopen, md5, log, remove):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        urlretrieve.return_value = (None, {})
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        self.assertRaises(AssertionError, tasks.fetch_job_artifacts, 'job_name')
        assert not taropen.called
        remove.assert_called_once_with('job_path/job_name.tgz')

    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_checksum_mismatch(
            self, OrchRelation, get_job_path, urlretrieve,
            taropen, mkdir, mopen, md5, log, remove):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        urlretrieve.return_value = (None, {'ETag': '"ca11ab1e"'})
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        self.assertRaises(AssertionError, tasks.fetch_job_artifacts, 'job_name')
        assert not taropen.called
        remove.assert_called_once_with('job_path/job_name.tgz')

    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_same_version(self, OrchRelation, get_job_path, exists, urlretrieve, taropen):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        exists.return_value = True
        tasks.fetch_job_artifacts('job_name')
        assert not urlretrieve.called
        assert not taropen.called

    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('cloudfoundry.tasks.urllib.urlretrieve')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_retry(self, OrchRelation, get_job_path, urlretrieve,
                                       taropen, mkdir, mopen, md5, log, remove):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        urlretrieve.side_effect = [
            urllib.ContentTooShortError('too short', {}),
            (None, {'ETag': '"deadbeef"'})]
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        tgz = taropen.return_value.__enter__.return_value
        tasks.fetch_job_artifacts('job_name')
        self.assertEqual(urlretrieve.call_args_list, [mock.call(
            'http://url/cf-version/amd64/job_name',
            'job_path/job_name.tgz')]*2)
        md5.assert_called_once_with('read')
        taropen.assert_called_once_with('job_path/job_name.tgz')
        tgz.extractall.assert_called_once_with('job_path')
        log.assert_called_with('Unable to download artifact: too short; retrying (attempt 1 of 3)', 'INFO')

    @mock.patch('os.symlink')
    @mock.patch('os.unlink')
    @mock.patch('shutil.copytree')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_install_job_packages(self, OrchRelation, get_job_path, exists, copytree, unlink, symlink):
        get_job_path.return_value = 'job_path'
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version'}]}
        exists.side_effect = [False, True]
        tasks.install_job_packages('job_name')
        self.assertEqual(exists.call_args_list, [
            mock.call('/var/vcap/packages/version/job_name'),
            mock.call('/var/vcap/packages/job_name'),
        ])
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
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version'}]}
        exists.return_value = True
        tasks.install_job_packages('job_name')
        exists.assert_called_once_with('/var/vcap/packages/version/job_name')
        assert not copytree.called
        assert not unlink.called
        assert not symlink.called

    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_get_job_path(self, OrchRelation):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version'}]}
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

    @mock.patch('os.path.exists')
    @mock.patch('os.symlink')
    @mock.patch('os.unlink')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    @mock.patch('cloudfoundry.tasks.load_spec')
    @mock.patch('cloudfoundry.templating.RubyTemplateCallback')
    def test_job_templates(self, RubyTemplateCallback, load_spec, OrchRelation, unlink, symlink, exists):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version'}]}
        spec = load_spec.return_value = {'templates': {
            'src1': 'dest1',
            'src2': 'dest2',
        }}
        exists.return_value = True
        manager = mock.Mock()
        generated_callbacks = RubyTemplateCallback.side_effect = [
            mock.Mock(), mock.Mock(services.ManagerCallback()), mock.Mock()]
        tasks.job_templates('map')(manager, 'job_name', 'event_name')
        generated_callbacks[0].assert_called_once_with('job_name')
        generated_callbacks[1].assert_called_once_with(manager, 'job_name', 'event_name')
        expected_calls = [
            mock.call('src1', '/var/vcap/jobs/version/job_name/dest1', 'map', spec,
                      templates_dir='charm_dir/jobs/version/job_name/templates'),
            mock.call('src2', '/var/vcap/jobs/version/job_name/dest2', 'map', spec,
                      templates_dir='charm_dir/jobs/version/job_name/templates'),
            mock.call('monit', '/var/vcap/jobs/version/job_name/monit/job_name.cfg', 'map', spec,
                      templates_dir='charm_dir/jobs/version/job_name'),
        ]
        for expected_call in expected_calls:
            self.assertIn(expected_call, RubyTemplateCallback.call_args_list)
        self.assertEqual(RubyTemplateCallback.call_count, len(expected_calls))
        load_spec.assert_called_once_with('job_name')
        self.assertEqual(unlink.call_args_list, [
            mock.call('/var/vcap/jobs/job_name'),
            mock.call('/etc/monit.d/job_name.cfg'),
        ])
        self.assertEqual(symlink.call_args_list, [
            mock.call('/var/vcap/jobs/version/job_name', '/var/vcap/jobs/job_name'),
            mock.call('/var/vcap/jobs/version/job_name/monit/job_name.cfg', '/etc/monit.d/job_name.cfg'),
        ])

    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_build_service_block(self, relation_ids, mconfig):
        relation_ids.return_value = []
        services = tasks.build_service_block('router-v1')
        self.assertEqual(services[0]['provided_data'], [])
        self.assertIsInstance(services[0]['required_data'][0],
                              contexts.OrchestratorRelation)
        self.assertIsInstance(services[0]['required_data'][1],
                              contexts.NatsRelation)
        # Show that we converted to rubytemplatecallbacks
        self.assertIsInstance(services[0]['data_ready'][2],
                              tasks.JobTemplates)
