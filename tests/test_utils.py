import json
import mock
import pkg_resources
import unittest

from cloudfoundry import utils


class TestUtils(unittest.TestCase):
    @mock.patch('subprocess.check_output')
    def test_current_env(self, check_output):
        utils.current_env()
        check_output.assert_called_once_with(['juju', 'switch'])

    def test_flatten_relations(self):
        r = utils.flatten_relations([
            ['mysql', ['a', 'b']],
            ['website', 'c']])
        self.assertEqual(r, set((
            ('a', 'mysql'),
            ('b', 'mysql'),
            ('c', 'website'))))

    def test_flatten_reality(self):
        data = json.loads(
            pkg_resources.resource_string(__name__, 'status.json'))

        r = utils.flatten_reality(data)
        self.assertEqual(r,
                         set([(u'etcd', u'etcd:cluster'),
                              (u'mysql', u'mysql:cluster'),
                              (u'nats', u'router:nats'),
                              (u'nats:nats', u'router')])
                         )

    def test_rel_exists(self):
        data = json.loads(
            pkg_resources.resource_string(__name__, 'status.json'))
        self.assertTrue(utils.rel_exists(data, 'etcd', 'etcd:cluster'))
        self.assertTrue(utils.rel_exists(data, 'etcd:cluster', 'etcd'))

        self.assertTrue(utils.rel_exists(data, 'nats', 'router:nats'))
        self.assertTrue(utils.rel_exists(data, 'router:nats', 'nats'))

        self.assertFalse(utils.rel_exists(data, 'nats', 'rabbitmq'))

    def test_deep_merge(self):
        initial = {'properties': {'job1': {'prop1': 'val1'}, 'job2': None}}
        additional = {'properties': {'job1': {'prop2': 'val2'}, 'job2': {'prop3': 'val3'}}}
        expected = {
            'properties': {
                'job1': {'prop1': 'val1', 'prop2': 'val2'},
                'job2': {'prop3': 'val3'},
            },
        }
        actual = utils.deepmerge(initial, additional)
        self.assertEqual(actual, expected)

    def test_nested_dict(self):
        nd = utils.NestedDict()
        nd['foo.bar.baz'] = 'qux'
        nd['foo.moo'] = 'mux'
        self.assertEqual(nd, {
            'foo': {
                'bar': {'baz': 'qux'},
                'moo': 'mux',
            }
        })

        self.assertEqual(nd['foo.bar.baz'], 'qux')

    def test_nested_dict_iterable(self):
        nd = utils.NestedDict((('a', 'b'),
                               ('b.c.d', 1)))
        self.assertEqual(nd['a'], 'b')
        self.assertEqual(nd['b.c.d'], 1)

    def test_nested_dict_init(self):
        nd = utils.NestedDict({'a': 'b', 'b.c.d': 1})
        self.assertEqual(nd['a'], 'b')
        self.assertEqual(nd['b.c.d'], 1)
        self.assertEqual(nd['b']['c']['d'], 1)

    def test_parse_config(self):
        fn = pkg_resources.resource_filename(__name__, 'server.conf')
        conf = utils.parse_config(fn)
        self.assertEqual(conf['credentials.user'], 'user-admin')
        self.assertEqual(conf['credentials.password'], 'xxx-admin')
        self.assertEqual(conf['server.port'], 8888)
        self.assertEqual(conf['server.repository'], 'build')

    def test_parse_config_with_defaults(self):
        fn = pkg_resources.resource_filename(__name__, 'server.conf')
        conf = utils.parse_config(fn, utils.NestedDict({
            'server.port': 8000,
            'server.address': '127.0.0.1',
        }))
        self.assertEqual(conf['credentials.user'], 'user-admin')
        self.assertEqual(conf['credentials.password'], 'xxx-admin')
        self.assertEqual(conf['server.port'], 8888)
        self.assertEqual(conf['server.address'], '127.0.0.1')
        self.assertEqual(conf['server.repository'], 'build')
