#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from cloudfoundry.mapper import property_mapper, flatten, NestedDict


class TestMapper(unittest.TestCase):
    def test_nested_dict(self):
        nd = NestedDict()
        nd['foo.bar.baz'] = 'qux'
        nd['foo.moo'] = 'mux'
        self.assertEqual(nd, {
            'foo': {
                'bar': {'baz': 'qux'},
                'moo': 'mux',
            }
        })

    def test_flatten(self):
        result = flatten({
            'foo': {
                'bar': {'qux': 'moo'},
                'mux': 'blag',
            }
        })
        self.assertEqual(result, {
            'foo.bar.qux': 'moo',
            'foo.mux': 'blag',
        })

    def test_property_mapper(self):
        result = property_mapper([
            ('nats.port', 'properties.nats.network.port'),
            ('nats.(\w+)', r'properties.nats.\1')
        ], {'nats': {'port': 1234, 'host': '0.0.0.0'}})

        self.assertEqual(result['properties']['nats']['network']['port'], 1234)
        self.assertEqual(result['properties']['nats']['host'], '0.0.0.0')
        self.assertNotIn('port', result['properties']['nats'])


if __name__ == '__main__':
    unittest.main()
