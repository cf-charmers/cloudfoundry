#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import mock

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

    def test_property_mapper_name_mapping(self):
        data_source = NestedDict({'foo': {'bar': 'FOO'}})
        data_source.name = 'foo'
        mapping = mock.Mock(return_value={'FOO.bar': 'qux'})
        result = property_mapper({'foo': mapping}, data_source)
        self.assertEqual(result, {'FOO': {'bar': 'qux'}})
        mapping.assert_called_once_with({'foo': {'bar': 'FOO'}})

    def test_property_mapper_erb_mapping(self):
        erb_mapping = mock.Mock(return_value={'FOO': 'bar'})
        data_source = mock.Mock(object, erb_mapping=erb_mapping)
        result = property_mapper({}, data_source)
        self.assertEqual(result, {'FOO': 'bar'})
        erb_mapping.assert_called_once_with()

    def test_property_mapper_key_mapping(self):
        data_source = NestedDict({'bar': {'bar': 'FOO'}})
        data_source.name = 'foo'
        mapping = mock.Mock(return_value={'FOO': 'bar'})
        result = property_mapper({'bar': mapping}, data_source)
        self.assertEqual(result, {'FOO': 'bar'})
        mapping.assert_called_once_with({'bar': 'FOO'})

    def test_property_mapper_no_mapping(self):
        data_source = NestedDict({'foo': {'bar': 'FOO'}})
        mapping = mock.Mock(return_value={'FOO': 'bar'})
        result = property_mapper({'bar': mapping}, data_source)
        self.assertEqual(result, {'foo': {'bar': 'FOO'}})
        assert not mapping.called


if __name__ == '__main__':
    unittest.main()
