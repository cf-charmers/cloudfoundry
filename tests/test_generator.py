#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
from contextlib import contextmanager

import yaml

from charmgen.generator import CharmGenerator
from cloudfoundry.contexts import OrchestratorRelation

from charmhelpers.contrib.cloudfoundry import contexts

# Local fixture
from tests.release1 import RELEASES, SERVICES


@contextmanager
def tempdir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


class TestGenerator(unittest.TestCase):

    def test_select_release(self):
        g = CharmGenerator(RELEASES, SERVICES)
        self.assertRaises(KeyError, g.select_release, 'anything')
        self.assertRaises(KeyError, g.select_release, 153)

        self.assertEquals(g.select_release(171), RELEASES[-1])
        self.assertEquals(g.select_release('171'), RELEASES[-1])
        self.assertEquals(g.select_release(172), RELEASES[-1])
        self.assertEquals(g.select_release(173), RELEASES[0])
        # Tests the open range
        self.assertEquals(g.select_release(199), RELEASES[0])
        self.assertEquals(g.release, RELEASES[0])
        self.assertEquals(g.release_version, 199)

    def test_build_metadata(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        cc = g.release['topology']['services'][0][0]
        meta = g.build_metadata(cc)
        self.assertEqual(meta['name'], 'cloud_controller_v1')
        self.assertEqual(meta['author'], CharmGenerator.author)
        cc_service = SERVICES[cc]
        self.assertEqual(meta['summary'], cc_service['summary'])
        self.assertEqual(meta['description'], cc_service['description'])

        # Interface generation
        provides = meta['provides']
        requires = meta['requires']
        self.assertEqual(provides[contexts.CloudControllerRelation.name][
            'interface'], contexts.CloudControllerRelation.interface)
        self.assertEqual(requires[contexts.NatsRelation.name]['interface'],
                         contexts.NatsRelation.interface)
        self.assertEqual(requires[contexts.RouterRelation.name]['interface'],
                         contexts.RouterRelation.interface)
        # This interface is added implicitly by our model, generated
        # charms have a relation to their Orchestrator.
        self.assertEqual(requires[OrchestratorRelation.name][
            'interface'], OrchestratorRelation.interface)

    def test_build_hooks(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        cc = g.release['topology']['services'][0]
        hooks = g.build_hooks(cc)
        self.assertIn('db-relation-changed', hooks)
        self.assertIn('nats-relation-joined', hooks)
        self.assertIn('orchestrator-relation-joined', hooks)
        self.assertIn('install', hooks)
        self.assertIn('start', hooks)

    def test_build_entry_point(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        cc = g.release['topology']['services'][0]
        entry = g.build_entry(cc)
        self.assertIn('job_manager("cloud_controller_v1")', entry)

    def test_generate_charm(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        cc = g.release['topology']['services'][0]
        with tempdir() as tmpdir:
            g.generate_charm(cc, tmpdir)
            self.assertTrue(os.path.exists(
                os.path.join(tmpdir, 'metadata.yaml')))
            self.assertTrue(os.path.isdir(
                os.path.join(tmpdir, 'hooks')))
            self.assertTrue(os.path.islink(
                os.path.join(tmpdir, 'hooks', 'db-relation-changed')))
            self.assertTrue(os.path.isfile(
                os.path.join(tmpdir, 'hooks', 'entry.py')))
            self.assertTrue(os.path.isfile(
                os.path.join(tmpdir, 'hooks', 'entry.py')))
            self.assertTrue(os.access(
                os.path.join(tmpdir, 'hooks', 'entry.py'),
                os.R_OK | os.X_OK))

    def test_build_charm_ref(self):
        g = CharmGenerator(RELEASES, SERVICES)
        self.assertEqual(g._build_charm_ref('cs:trusty/mysql'),
                         {'charm': 'cs:trusty/mysql'})
        self.assertEqual(g._build_charm_ref('cloud_controller_v1'),
                         {'branch': 'local:trusty/cloud_controller_v1'})

    def test_parse_charm_ref(self):
        g = CharmGenerator(RELEASES, SERVICES)
        self.assertEqual(g._parse_charm_ref('cs:trusty/mysql'),
                         ('cs:trusty/mysql', 'mysql', 'mysql'))
        self.assertEqual(g._parse_charm_ref(('cs:trusty/mysql', 'db')),
                         ('cs:trusty/mysql', 'mysql', 'db'))
        self.assertEqual(g._parse_charm_ref(('cloud_controller_v1', 'cc')),
                         ('cloud_controller_v1', 'cloud_controller_v1', 'cc'))

    def test_build_deployment(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        data = g.build_deployment()
        cf = data['cloudfoundry']
        self.assertEqual(cf['series'], 'trusty')
        # A local generated charm
        self.assertEqual(cf['services']['cc'],
                         {'branch': 'local:trusty/cloud_controller_v1'})
        # A store charm
        self.assertEqual(cf['services']['mysql'],
                         {'charm': 'cs:trusty/mysql'})

        # Relations
        rels = set(map(tuple, tuple(cf['relations'])))
        expected = ('mysql:db', ('cc:db',))
        # Verify we found expected relations
        self.assertIn(expected, rels)

    def test_generate_deployment(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        with tempdir() as tmpdir:
            g.generate_deployment(tmpdir)
            bundle = os.path.join(tmpdir, 'bundles.yaml')
            self.assertTrue(os.path.exists(bundle))
            with open(bundle) as fp:
                data = yaml.safe_load(fp)
                cf = data['cloudfoundry']
                self.assertEqual(cf['series'], 'trusty')

    def test_generate(self):
        g = CharmGenerator(RELEASES, SERVICES)
        g.select_release(173)
        with tempdir() as tmpdir:
            g.generate(tmpdir)
            self.assertTrue(os.path.exists(
                os.path.join(tmpdir, 'bundles.yaml')))
            self.assertTrue(os.path.exists(os.path.join(
                tmpdir, 'trusty', 'cloud_controller_v1')))
            # While generate doesn't create a mysql charm (it's from cs)
            # deployer will eventually place it in this dir pre-deploy
            self.assertFalse(os.path.exists(os.path.join(
                tmpdir, 'trusty', 'mysql')))
            self.assertTrue(os.path.isdir(os.path.join(
                tmpdir, 'trusty', 'cloud_controller_v1', 'hooks', 'cloudfoundry')))
            self.assertTrue(os.path.isdir(os.path.join(
                tmpdir, 'trusty', 'cloud_controller_v1', 'files')))


if __name__ == '__main__':
    unittest.main()
