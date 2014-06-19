#!/usr/bin/env python
# -*- coding: utf-8 -*-
import mock
import unittest

from charmgen import contexts


class TestContexts(unittest.TestCase):

    @mock.patch('charmhelpers.core.hookenv.relation_ids')
    def test_orchestrator_required_keys(self, mrel_ids):
        oc = contexts.OrchestratorRelation()
        self.assertEqual(oc.required_keys, ['domain'])

if __name__ == '__main__':
    unittest.main()
