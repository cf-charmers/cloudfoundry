import unittest
import mock
import urllib

from charmhelpers.core import services
from cloudfoundry import contexts
from cloudfoundry.path import path
from cloudfoundry import tasks


class TestTasks(unittest.TestCase):
    def setUp(self):
        self.charm_dir_patch = mock.patch(
            'charmhelpers.core.hookenv.charm_dir')
        self.charm_dir = self.charm_dir_patch.start()
        self.charm_dir.return_value = 'charm_dir'

    def tearDown(self):
        self.charm_dir_patch.stop()

    @mock.patch('charmhelpers.core.host.adduser')
    @mock.patch('subprocess.check_call')
    @mock.patch('charmhelpers.fetch.filter_installed_packages')
    @mock.patch('charmhelpers.fetch.apt_install')
    def test_install_base_dependencies(self, apt_install,
                                       filter_installed_packages,
                                       check_call, adduser):
        filter_installed_packages.side_effect = lambda a: a
        with mock.patch('cloudfoundry.tasks.path', spec=path) as monitrc:
            monitrc().exists.return_value = False
            tasks.install_base_dependencies()

        apt_install.assert_called_once_with(packages=[
            'ruby', 'monit', 'runit'])
        adduser.assert_called_once_with('vcap')
        assert monitrc.called
        assert monitrc.call_args == mock.call('/etc/monit/conf.d/enable_http')
        newtext = '\nset httpd port 2812 and\n'\
            '   use address localhost\n'\
            '   allow localhost\n'
        assert monitrc().write_text.call_args == mock.call(newtext)
        check_call.assert_has_calls([
            mock.call(['service', 'monit', 'force-reload'], -2),
            mock.call(['gem', 'install',
                       '--no-ri', '--no-rdoc',
                       'charm_dir/files/' +
                       'bosh-template-1.2611.0.pre.gem'])])

    def test_monit_http_enable_idem(self):
        with mock.patch('cloudfoundry.tasks.path', spec=path) as confd:
            confd().exists.return_value = True
            tasks.enable_monit_http_interface()
            assert not confd().write_text.called

    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('subprocess.check_call')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts(self, OrchRelation, get_job_path, check_call,
                                 taropen, mkdir, mopen, md5, log, remove):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        mopen.return_value.__enter__().read.return_value = 'read'
        #md5.return_value.hexdigest.return_value = 'deadbeef'
        tgz = taropen.return_value.__enter__.return_value
        tasks.fetch_job_artifacts('job_name')
        check_call.assert_called_once_with([
            'wget', '-t0', '-c', '-nv',
            'http://url/cf-version/amd64/job_name',
            '-O', 'job_path/job_name.tgz'])
        #md5.assert_called_once_with('read')
        taropen.assert_called_once_with('job_path/job_name.tgz')
        tgz.extractall.assert_called_once_with('job_path')

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('subprocess.check_call')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    @unittest.skip('temporarily disabled')
    def test_fetch_job_artifacts_missing_checksum(
            self, OrchRelation, get_job_path, check_call,
            taropen, mkdir, mopen, md5, log, remove, exists):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        #urlretrieve.return_value = (None, {})
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        exists.side_effect = [False, True]
        self.assertRaises(AssertionError, tasks.fetch_job_artifacts, 'job_name')
        assert not taropen.called
        remove.assert_called_once_with('job_path/job_name.tgz')

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('hashlib.md5')
    @mock.patch('cloudfoundry.tasks.open', create=True)
    @mock.patch('charmhelpers.core.host.mkdir')
    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('subprocess.check_call')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    @unittest.skip('temporarily disabled')
    def test_fetch_job_artifacts_checksum_mismatch(
            self, OrchRelation, get_job_path, check_call,
            taropen, mkdir, mopen, md5, log, remove, exists):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        #urlretrieve.return_value = (None, {'ETag': '"ca11ab1e"'})
        mopen.return_value.__enter__().read.return_value = 'read'
        md5.return_value.hexdigest.return_value = 'deadbeef'
        exists.side_effect = [False, True]
        self.assertRaises(AssertionError, tasks.fetch_job_artifacts, 'job_name')
        assert not taropen.called
        remove.assert_called_once_with('job_path/job_name.tgz')

    @mock.patch('cloudfoundry.tasks.tarfile.open')
    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_fetch_job_artifacts_same_version(self, OrchRelation, get_job_path, exists, check_call, taropen):
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version',
                                     'artifacts_url': 'http://url'}]}
        get_job_path.return_value = 'job_path'
        exists.return_value = True
        tasks.fetch_job_artifacts('job_name')
        assert not check_call.called
        assert not taropen.called

    @mock.patch('os.symlink')
    @mock.patch('os.unlink')
    @mock.patch('os.path.exists')
    @mock.patch('cloudfoundry.tasks.get_job_path')
    @mock.patch('cloudfoundry.contexts.OrchestratorRelation')
    def test_install_job_packages(self, OrchRelation, get_job_path, exists, unlink, symlink):
        get_job_path.return_value = 'job_path'
        OrchRelation.return_value = {'orchestrator': [{'cf_version': 'version'}]}
        exists.side_effect = [False, True, True]
        filename = 'package-123abc.tgz'

        script = mock.Mock(name='script', spec=path)
        script.stat().st_mode = 33204
        script.basename.return_value = filename

        with mock.patch('subprocess.check_call') as cc,\
          mock.patch('cloudfoundry.tasks.path', spec=path) as pth:
            pkgdir = pth('pkgdir')
            pkgdir.exists.return_value = False

            reldir = pth('reldir')
            files = (pth() / 'packages').files
            files.name = 'files'
            files.return_value = [script]
            pkgpath = reldir.__div__().__div__().__div__()
            pkgpath.exists.return_value = False
            pkgdest = pkgdir.__div__()

            pkgdest.exists.return_value = False
            tasks.install_job_packages(pkgdir, reldir,  'job_name')

            assert cc.called
            cc.assert_called_once_with(['tar', '-xzf', script])

            assert reldir.makedirs_p.called
            pkgpath.symlink.assert_called_once_with(pkgdir / 'package')

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
            mock.call('/etc/monit/conf.d/job_name'),
        ])
        self.assertEqual(symlink.call_args_list, [
            mock.call('/var/vcap/jobs/version/job_name', '/var/vcap/jobs/job_name'),
            mock.call('/var/vcap/jobs/version/job_name/monit/job_name.cfg', '/etc/monit/conf.d/job_name'),
        ])

    @mock.patch('charmhelpers.core.hookenv.unit_get')
    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_build_service_block(self, relation_ids, mconfig, unit_get):
        relation_ids.return_value = []
        unit_get.return_value = 'unit/0'
        services = tasks.build_service_block('router-v1')
        self.assertIsInstance(services[0]['provided_data'][0],
                              contexts.RouterRelation)
        self.assertIsInstance(services[0]['required_data'][0],
                              contexts.OrchestratorRelation)
        self.assertIsInstance(services[0]['required_data'][1],
                              contexts.NatsRelation)
        # Show that we converted to rubytemplatecallbacks
        self.assertIsInstance(services[0]['data_ready'][2],
                              tasks.JobTemplates)
