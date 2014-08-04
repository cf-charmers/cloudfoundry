#!/usr/bin/env python
# -*- coding: utf-8 -*-
import mock
import unittest
import os
import tempfile
from cloudfoundry import contexts

# Used for path of context mocks
CONTEXT = 'cloudfoundry.contexts.'


class TestNatsRelation(unittest.TestCase):

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_nats_relation_empty(self, mid):
        mid.return_value = None
        n = contexts.NatsRelation()
        self.assertEqual(n, {})

    @mock.patch('charmhelpers.core.hookenv.related_units')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch('charmhelpers.core.hookenv.relation_get')
    def test_nats_relation_populated(self, mrel, mid, mrelated):
        mid.return_value = ['nats']
        mrel.return_value = {'port': 1234, 'address': 'host',
                             'user': 'user', 'password': 'password'}
        mrelated.return_value = ['router/0']
        n = contexts.NatsRelation()
        expected = {'nats': [{'port': 1234, 'address': 'host',
                              'user': 'user', 'password': 'password'}]}
        self.assertTrue(bool(n))
        self.assertEqual(n, expected)
        self.assertEqual(n['nats'][0]['port'], 1234)

    @mock.patch('charmhelpers.core.hookenv.related_units')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch('charmhelpers.core.hookenv.relation_get')
    def test_nats_relation_partial(self, mrel, mid, mrelated):
        mid.return_value = ['nats']
        mrel.return_value = {'address': 'host'}
        mrelated.return_value = ['router/0']
        n = contexts.NatsRelation()
        self.assertEqual(n, {'nats': []})

    @mock.patch(CONTEXT + 'NatsRelation.get_data')
    @mock.patch('charmhelpers.core.host.pwgen')
    @mock.patch(CONTEXT + 'StoredContext')
    def test_get_credentials(self, mStoredContext, mpwgen, mget_data):
        mpwgen.side_effect = ['u', 'p']
        mStoredContext.side_effect = lambda f, d: d
        self.assertEqual(contexts.NatsRelation().get_credentials(), {
            'user': 'u',
            'password': 'p',
        })

    @mock.patch(CONTEXT + 'NatsRelation.get_data')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    @mock.patch(CONTEXT + 'NatsRelation.get_credentials')
    def test_provide_data(self, mget_credentials, munit_get, mget_data):
        mget_credentials.return_value = {'user': 'user',
                                         'password': 'password'}
        munit_get.return_value = '127.0.0.1'
        self.assertEqual(contexts.NatsRelation().provide_data(), {
            'user': 'user',
            'password': 'password',
            'port': 4222,
            'address': '127.0.0.1',
        })


class TestMysqlRelation(unittest.TestCase):
    @mock.patch('charmhelpers.core.services.RelationContext.is_ready')
    @mock.patch('charmhelpers.core.services.RelationContext.get_data')
    def test_get_data(self, mget_data, mis_ready):
        mis_ready.side_effect = [False, True]
        relation = contexts.MysqlRelation()
        relation.update({
            'db': [{
                'user': 'user',
                'password': 'password',
                'host': 'host',
                'database': 'database',
            }],
        })
        relation.get_data()
        self.assertEqual(relation, {
            'db': [{
                'user': 'user',
                'password': 'password',
                'host': 'host',
                'database': 'database',
                'dsn': 'mysql2://user:password@host:3306/database',
                'port': '3306',
            }],
        })


class TestLTCRelation(unittest.TestCase):
    @mock.patch(CONTEXT + 'LTCRelation.get_data')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    @mock.patch('charmhelpers.core.host.pwgen')
    @mock.patch(CONTEXT + 'StoredContext')
    def test_get_shared_secret(self, mStoredContext, mpwgen,
                               mcharm_dir, mget_data):
        mStoredContext.side_effect = lambda f, d: d
        mpwgen.return_value = 'secret'
        self.assertEqual(contexts.LTCRelation().get_shared_secret(),
                         'secret')

    @mock.patch(CONTEXT + 'LTCRelation.get_data')
    @mock.patch(CONTEXT + 'LTCRelation.get_shared_secret')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    def test_provide_data(self, munit_get, mget_shared_secret, mget_data):
        munit_get.return_value = 'address'
        mget_shared_secret.return_value = 'secret'
        self.assertEqual(contexts.LTCRelation().provide_data(), {
            'host': 'address',
            'port': contexts.LTCRelation.incoming_port,
            'outgoing_port': contexts.LTCRelation.outgoing_port,
            'shared_secret': 'secret',
        })


class TestLoggregatorRelation(unittest.TestCase):
    @mock.patch(CONTEXT + 'LoggregatorRelation.get_data')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    def test_provide_data(self, munit_get, mget_data):
        munit_get.return_value = 'address'
        self.assertEqual(contexts.LoggregatorRelation().provide_data(), {
            'address': 'address',
            'incoming_port': contexts.LoggregatorRelation.incoming_port,
            'outgoing_port': contexts.LoggregatorRelation.outgoing_port,
        })


class TestCloudControllerRelation(unittest.TestCase):
    @mock.patch(CONTEXT + 'CloudControllerRelation.get_data')
    @mock.patch('charmhelpers.core.host.pwgen')
    @mock.patch(CONTEXT + 'StoredContext')
    def test_get_credentials(self, mStoredContext, mpwgen, mget_data):
        mStoredContext.side_effect = lambda f, d: d
        mpwgen.side_effect = ['user', 'password', 'db-key']
        self.assertEqual(contexts.CloudControllerRelation().get_credentials(),
                         {'user': 'user',
                          'password': 'password',
                          'db_encryption_key': 'db-key',
                          })

    @mock.patch(CONTEXT + 'CloudControllerRelation.get_data')
    @mock.patch(CONTEXT + 'CloudControllerRelation.get_credentials')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    def test_provide_data(self, munit_get, mget_credentials, mget_data):
        munit_get.return_value = 'address'
        mget_credentials.return_value = {
            'user': 'user',
            'password': 'password',
        }
        self.assertEqual(contexts.CloudControllerRelation().provide_data(), {
            'user': 'user',
            'password': 'password',
            'hostname': 'address',
            'port': 9022,
        })


class TestStoredContext(unittest.TestCase):

    def test_context_saving(self):
        _, file_name = tempfile.mkstemp()
        os.unlink(file_name)
        self.assertFalse(os.path.isfile(file_name))
        contexts.StoredContext(file_name, {'key': 'value'})
        self.assertTrue(os.path.isfile(file_name))

    def test_restoring(self):
        _, file_name = tempfile.mkstemp()
        os.unlink(file_name)
        contexts.StoredContext(file_name, {'key': 'initial_value'})
        self.assertTrue(os.path.isfile(file_name))
        context = contexts.StoredContext(file_name, {'key': 'random_value'})
        self.assertIn('key', context)
        self.assertEqual(context['key'], 'initial_value')

    def test_stored_context_raise(self):
        _, file_name = tempfile.mkstemp()
        with self.assertRaises(OSError):
            contexts.StoredContext(file_name, {'key': 'initial_value'})
        os.unlink(file_name)


class TestOrchestratorRelation(unittest.TestCase):
    @mock.patch('charmhelpers.core.services.RelationContext.get_data', mock.Mock())
    @mock.patch('charmhelpers.core.hookenv.unit_private_ip')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_provide_data(self, config, upi):
        config.return_value = {'cf_version': 170, 'domain': 'domain'}
        upi.return_value = 'upi'
        result = contexts.OrchestratorRelation().provide_data()
        self.assertEqual(result, {
            'artifacts_url': 'http://upi:8019',
            'cf_version': 170,
            'domain': 'domain',
        })

    @mock.patch('charmhelpers.core.services.RelationContext.get_data', mock.Mock())
    @mock.patch('charmhelpers.core.hookenv.unit_private_ip')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_provide_data_latest(self, config, upi):
        config.return_value = {'cf_version': 'latest', 'domain': 'domain'}
        upi.return_value = 'upi'
        result = contexts.OrchestratorRelation().provide_data()
        self.assertEqual(result, {
            'artifacts_url': 'http://upi:8019',
            'cf_version': 173,
            'domain': 'domain',
        })

    @mock.patch(CONTEXT + 'OrchestratorRelation.get_data')
    @mock.patch('subprocess.check_output')
    def test_to_ip_already_ip(self, mcheck_output, mget_data):
        self.assertEqual(contexts.OrchestratorRelation().to_ip('127.0.0.1'),
                         '127.0.0.1')

    @mock.patch(CONTEXT + 'OrchestratorRelation.get_data')
    @mock.patch('subprocess.check_output')
    def test_to_ip(self, mcheck_output, mget_data):
        mcheck_output.return_value = ' foo.maas\n 0.0.0.0\n'
        self.assertEqual(contexts.OrchestratorRelation().to_ip('foo'), '0.0.0.0')

    @mock.patch(CONTEXT + 'OrchestratorRelation.get_data')
    @mock.patch('subprocess.check_output')
    def test_to_ip_none(self, mcheck_output, mget_data):
        mcheck_output.return_value = ' foo.maas\n bar\n'
        self.assertEqual(contexts.OrchestratorRelation().to_ip('foo'), None)

    @mock.patch('cloudfoundry.api.APIEnvironment')
    @mock.patch(CONTEXT + 'JujuAPICredentials')
    @mock.patch(CONTEXT + 'OrchestratorRelation.get_data', mock.Mock())
    @mock.patch(CONTEXT + 'OrchestratorRelation.to_ip')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_get_domain(self, mconfig, mto_ip, api_creds, api_env):
        mconfig.return_value = {'domain': 'foo'}
        self.assertEqual(contexts.OrchestratorRelation().get_domain(), 'foo')

        mconfig.return_value = {'domain': 'xip.io'}
        api_creds.return_value = {'api_address': 'addr', 'api_password': 'pw'}
        api_env.return_value.status.return_value = {'services': {}}
        self.assertEqual(contexts.OrchestratorRelation().get_domain(),
                         'xip.io')
        api_creds.assert_called_once_with()
        api_env.assert_called_with('addr', 'pw')
        api_env.return_value.connect.assert_called_once_with()

        api_env.return_value.status.return_value = {
            'services': {
                'cloudfoundry': {},
                'haproxy': {
                    'units': {
                        'haproxy/1': {'public-address': 'unit-1-addr'},
                        'haproxy/0': {'public-address': 'unit-0-addr'},
                    },
                },
            },
        }
        mto_ip.return_value = '0.0.0.0'
        self.assertEqual(contexts.OrchestratorRelation().get_domain(),
                         '0.0.0.0.xip.io')
        mto_ip.assert_called_once_with('unit-0-addr')


class TestJujuAPICredentials(unittest.TestCase):
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_not_ready(self, config):
        config.return_value = {}
        self.assertEqual(contexts.JujuAPICredentials(), {})

    @mock.patch.object(contexts.JujuAPICredentials, 'get_api_address')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_ready(self, config, gaa):
        config.return_value = {'admin_secret': 'secret'}
        gaa.return_value = 'address'
        self.assertEqual(contexts.JujuAPICredentials(), {
            'api_address': 'wss://address',
            'api_password': 'secret',
        })

    @mock.patch('charmhelpers.core.hookenv.config', dict)
    @mock.patch('os.getenv')
    def test_get_api_address_env(self, getenv):
        getenv.return_value = 'address something'
        creds = contexts.JujuAPICredentials()
        self.assertEqual(creds.get_api_address(), 'address')

    @mock.patch('charmhelpers.core.hookenv.config', dict)
    @mock.patch('os.getenv', mock.Mock(return_value=None))
    @mock.patch('os.listdir')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    def test_get_api_address_not_found(self, charm_dir, listdir):
        charm_dir.return_value = '/agent_dir/unit_dir/charm_dir'
        listdir.return_value = ['foo', 'bar']
        creds = contexts.JujuAPICredentials()
        self.assertRaises(IOError, creds.get_api_address)
        listdir.assert_called_once_with('/agent_dir')

    @mock.patch('charmhelpers.core.hookenv.config', dict)
    @mock.patch('os.getenv', mock.Mock(return_value=None))
    @mock.patch('yaml.load')
    @mock.patch('cloudfoundry.contexts.open', create=True)
    @mock.patch('os.listdir')
    def test_get_api_address_found(self, listdir, mopen, yload):
        listdir.return_value = ['unit-foo', 'machine-bar']
        creds = contexts.JujuAPICredentials()
        yload.return_value = {'apiinfo': {'addrs': ['address', 'something']}}
        self.assertEqual(creds.get_api_address('/agent/unit'), 'address')
        listdir.assert_called_once_with('/agent')
        mopen.assert_called_once_with('/agent/machine-bar/agent.conf')


class TestArtifactCache(unittest.TestCase):
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_not_ready(self, config):
        config.return_value = {}
        self.assertEqual(contexts.ArtifactsCache(), {})

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_ready(self, config):
        config.return_value = {'artifacts_url': 'url'}
        self.assertEqual(contexts.ArtifactsCache(), {'artifacts_url': 'url'})


if __name__ == '__main__':
    unittest.main()
