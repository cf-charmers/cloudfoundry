import unittest
import mock

from cloudfoundry import templating


class TestTemplating(unittest.TestCase):
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
            '-C', '{"data": ["port", 80]}'])
        write_file.assert_called_once_with('target', 'test-data', 'root', 'root', 0444)

    @mock.patch.object(templating.RubyTemplateCallback, 'collect_data')
    @mock.patch.object(templating, 'render_erb')
    def test_ruby_template_callback(self, render_erb, collect_data):
        collect_data.return_value = {}
        callback = templating.RubyTemplateCallback(
            'source', 'target', 'owner', 'group', 0555, 'templates_dir')
        callback('manager', 'service_name', 'event_name')
        collect_data.assert_called_once_with('manager', 'service_name')
        render_erb.assert_called_once_with(
            'source', 'target', {}, 'owner', 'group', 0555, 'templates_dir')

    def test_deep_merge(self):
        initial = {'properties': {'job': {'prop1': 'val1'}}}
        additional = {'properties': {'job': {'prop2': 'val2'}}}
        expected = {
            'properties': {
                'job': {'prop1': 'val1', 'prop2': 'val2'},
            },
        }
        actual = templating.deepmerge(initial, additional)
        self.assertEqual(actual, expected)

    def test_ruby_template_callback_collect_data(self):
        manager = mock.Mock()
        manager.get_service.return_value = {
            'required_data': [
                {'properties': {'job1': {'prop1': 'val1'}}},
                {'properties': {'job2': {'prop2': 'val2'}}},
                {'properties': {'job2': {'prop3': 'val3'}}},
            ],
        }
        callback = templating.RubyTemplateCallback('source', 'target')
        context = callback.collect_data(manager, 'service_name')
        self.assertEqual(context, {
            'properties': {
                'job1': {'prop1': 'val1'},
                'job2': {'prop2': 'val2', 'prop3': 'val3'},
            },
        })
        manager.get_service.assert_called_once_with('service_name')
