#!/usr/bin/env python
# -*- coding: utf-8 -*-
import mock
import unittest

from cloudfoundry import contexts


class TestContexts(unittest.TestCase):

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_orchestrator_required_keys(self, mrel_ids):
        oc = contexts.OrchestratorRelation()
        self.assertEqual(set(oc.required_keys),
                         set(['domain', 'admin_secret', 'cf-version']))

if __name__ == '__main__':
    unittest.main()
