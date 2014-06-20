#!/usr/bin/env python
# -*- coding: utf-8 -*-
import mock
import unittest
import os
import tempfile
from cloudfoundry import contexts

# Used for path of context mocks
CONTEXT = 'cloudfoundry.contexts.'


class TestContexts(unittest.TestCase):

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_orchestrator_required_keys(self, mrel_ids):
        oc = contexts.OrchestratorRelation()
        self.assertEqual(set(oc.required_keys),
                         set(['domain', 'admin_secret',
                              'cf_version', 'artifacts_url']))


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


class TestRouterRelation(unittest.TestCase):

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_router_relation_empty(self, mid):
        mid.return_value = None
        n = contexts.RouterRelation()
        self.assertEqual(n, {})

    @mock.patch('charmhelpers.core.hookenv.related_units')
    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    @mock.patch('charmhelpers.core.hookenv.relation_get')
    def test_router_relation_populated(self, mrel, mid, mrelated):
        mid.return_value = ['router']
        mrel.return_value = {'domain': 'example.com'}
        mrelated.return_value = ['router/0']
        n = contexts.RouterRelation()
        expected = {'router': [{'domain': 'example.com'}]}
        self.assertTrue(bool(n))
        self.assertEqual(n, expected)
        self.assertEqual(n['router'][0]['domain'], 'example.com')

    @mock.patch(CONTEXT + 'RouterRelation.get_data')
    @mock.patch('subprocess.check_output')
    def test_to_ip_already_ip(self, mcheck_output, mget_data):
        self.assertEqual(contexts.RouterRelation().to_ip('127.0.0.1'),
                         '127.0.0.1')

    @mock.patch(CONTEXT + 'RouterRelation.get_data')
    @mock.patch('subprocess.check_output')
    def test_to_ip(self, mcheck_output, mget_data):
        mcheck_output.return_value = ' foo.maas\n 0.0.0.0\n'
        self.assertEqual(contexts.RouterRelation().to_ip('foo'), '0.0.0.0')

    @mock.patch(CONTEXT + 'RouterRelation.get_data')
    @mock.patch(CONTEXT + 'RouterRelation.to_ip')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_get_domain(self, mconfig, munit_get, mto_ip, mget_data):
        mconfig.return_value = {'domain': 'foo'}
        self.assertEqual(contexts.RouterRelation().get_domain(), 'foo')
        mconfig.return_value = {'domain': 'xip.io'}
        munit_get.return_value = 'my-domain.org'
        mto_ip.return_value = '0.0.0.0'
        self.assertEqual(contexts.RouterRelation().get_domain(),
                         '0.0.0.0.xip.io')
        mto_ip.assert_called_once_with('my-domain.org')

    @mock.patch(CONTEXT + 'RouterRelation.get_data')
    @mock.patch(CONTEXT + 'RouterRelation.get_domain')
    def test_provide_data(self, mget_domain, mget_data):
        mget_domain.return_value = 'my-domain.org'
        self.assertEqual(contexts.RouterRelation().provide_data(), {
            'domain': 'my-domain.org'})


class TestLogRouterRelation(unittest.TestCase):
    @mock.patch(CONTEXT + 'LogRouterRelation.get_data')
    @mock.patch('charmhelpers.core.hookenv.charm_dir')
    @mock.patch('charmhelpers.core.host.pwgen')
    @mock.patch(CONTEXT + 'StoredContext')
    def test_get_shared_secret(self, mStoredContext, mpwgen,
                               mcharm_dir, mget_data):
        mStoredContext.side_effect = lambda f, d: d
        mpwgen.return_value = 'secret'
        self.assertEqual(contexts.LogRouterRelation().get_shared_secret(),
                         'secret')

    @mock.patch(CONTEXT + 'LogRouterRelation.get_data')
    @mock.patch(CONTEXT + 'LogRouterRelation.get_shared_secret')
    @mock.patch('charmhelpers.core.hookenv.unit_get')
    def test_provide_data(self, munit_get, mget_shared_secret, mget_data):
        munit_get.return_value = 'address'
        mget_shared_secret.return_value = 'secret'
        self.assertEqual(contexts.LogRouterRelation().provide_data(), {
            'address': 'address',
            'incoming_port': contexts.LogRouterRelation.incoming_port,
            'outgoing_port': contexts.LogRouterRelation.outgoing_port,
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
        mpwgen.side_effect = ['user', 'password']
        self.assertEqual(contexts.CloudControllerRelation().get_credentials(),
                         {'user': 'user',
                          'password': 'password',
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

if __name__ == '__main__':
    unittest.main()
