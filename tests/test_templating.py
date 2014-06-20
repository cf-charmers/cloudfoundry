import unittest
import mock

from cloudfoundry import templating


class TestTemplating(unittest.TestCase):
    @mock.patch.object(templating.host, 'write_file')
    @mock.patch.object(templating.host, 'mkdir')
    @mock.patch.object(templating.host, 'log')
    @mock.patch.object(templating.subprocess, 'check_output')
    def test_render_erb(self, check_output, log, mkdir, write_file):
        context = {
            'data': ['port', 80],
        }
        self.charm_dir = 'charm_dir'
        check_output.return_value = 'test-data'
        templating.render_erb('fake_cc.erb', 'target', context, templates_dir='')
        check_output.assert_called_once_with([
            'bosh-template', 'fake_cc.erb', '-C', '{"data": ["port", 80]}'])
        write_file.assert_called_once_with('target', 'test-data', 'root', 'root', 0444)
