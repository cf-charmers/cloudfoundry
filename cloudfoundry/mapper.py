
class NestedDict(dict):
    def __setitem__(self, key, value):
        key = key.split('.')
        o = self
        for part in key[:-1]:
            o = o.setdefault(part, {})
        dict.__setitem__(o, key[-1], value)

    def update(self, other):
        for k, v in other.items():
            self[k] = v


def flatten(data):
    result = {}

    def _f(o, p):
        for k, v in o.items():
            if isinstance(v, dict):
                _f(v, p + [k])
            else:
                key = '.'.join(p + [k])
                result[key] = v
    _f(data, [])
    return result


def property_mapper(mapping, data_source):
    result = NestedDict()
    if getattr(data_source, 'name', None) in mapping:
        result.update(mapping[data_source.name](data_source))
    elif hasattr(data_source, 'erb_mapping'):
        result.update(data_source.erb_mapping())
    else:
        for key, value in data_source.iteritems():
            if key in mapping:
                result.update(mapping[key](value))
            else:
                result[key] = value
    return result
