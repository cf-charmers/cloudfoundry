import re


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


def property_mapper(property_expressions, data):
    data = flatten(data)
    result = NestedDict()
    for k, v in data.items():
        for input_re, dest_path in property_expressions:
            if re.match(input_re, k):
                if isinstance(dest_path, basestring):
                    target = re.sub(input_re, dest_path, k)
                    result[target] = v
                elif callable(dest_path):
                    new_data = dest_path(k, v)
                    result.update(new_data)
                break
    return result