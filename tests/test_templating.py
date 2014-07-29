import subprocess
import unittest
import mock

from cloudfoundry import templating


class TestTemplating(unittest.TestCase):
    maxDiff = None

    @mock.patch.object(templating.hookenv, 'charm_dir')
    @mock.patch.object(templating.host, 'write_file')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    @mock.patch.object(templating.subprocess, 'check_output')
    def test_render_erb(self, check_output, log, mkdir, write_file, charm_dir):
        context = {
            'data': ['port', 80],
        }
        charm_dir.return_value = 'charm_dir'
        check_output.return_value = 'test-data'
        templating.render_erb('fake_cc.erb', 'target', context)
        check_output.assert_called_once_with([
            'bosh-template', 'charm_dir/templates/fake_cc.erb',
            '-C', '{"data": ["port", 80]}'], stderr=subprocess.STDOUT)
        write_file.assert_called_once_with(
            'target', 'test-data', 'root', 'root', 0444)

    @mock.patch.object(templating.RubyTemplateCallback, 'collect_data')
    @mock.patch.object(templating, 'render_erb')
    def test_ruby_template_callback(self, render_erb, collect_data):
        collect_data.return_value = {}
        callback = templating.RubyTemplateCallback(
            'source', 'target', 'map', {'name': 'test', 'properties': {}},
            'owner', 'group', 0555, 'templates_dir')
        callback('manager', 'service_name', 'event_name')
        collect_data.assert_called_once_with('manager', 'service_name')
        render_erb.assert_called_once_with(
            'source', 'target', {}, 'owner', 'group', 0555, 'templates_dir')

    @mock.patch.object(templating.hookenv, 'local_unit')
    @mock.patch.object(templating.hookenv, 'unit_get')
    def test_ruby_template_callback_collect_data(self, unit_get, local_unit):
        unit_get.return_value = 'private-addr'
        local_unit.return_value = 'unit/0'
        relation_mock1 = mock.MagicMock()
        relation_mock1.name = 'foo'
        relation_mock2 = mock.MagicMock()
        relation_mock2.erb_mapping.return_value = {'job2.prop2': 'val2'}
        manager = mock.Mock()
        manager.get_service.return_value = {
            'required_data': [
                relation_mock1,
                relation_mock2,
                {'qux': {'prop4': 'val4'}},
            ],
        }
        mapping = {
            'foo': lambda v: {'job1.prop1': ['val1.1', 'val1.2']},
            'bar': lambda v: {'job2.prop3': 'val3'},
            'qux': lambda v: {'job2': v},
        }
        spec = {
            'foo': 'unused',
            'name': 'test',
            'properties': {
                'job1.prop1': {
                    'description': 'prop1',
                    'default': 'default1',
                },
                'job1.prop5': {
                    'description': 'prop5',
                    'default': 'default5',
                }
            },
        }
        callback = templating.RubyTemplateCallback(
            'source', 'target', mapping, spec)
        context = callback.collect_data(manager, 'service_name')
        self.assertEqual(context, {
            'index': 0,
            'job': {'name': 'test'},
            'networks': {'default': {'ip': 'private-addr'}},
            'properties': {
                'networks': {'apps': 'default'},
                'job1': {'prop1': ['val1.1', 'val1.2'], 'prop5': 'default5'},
                'job2': {'prop2': 'val2', 'prop4': 'val4'},
            },
        })
        manager.get_service.assert_called_once_with('service_name')
