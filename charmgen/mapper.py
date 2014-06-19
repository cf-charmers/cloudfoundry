import re


class NestedDict(dict):
    def __setitem__(self, key, value):
        key = key.split('.')
        o = self
        for part in key[:-1]:
            o = o.setdefault(part, {})
        o[key[-1]] = value


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
    for input_re, dest_path in property_expressions:
        for k, v in data.items():
            if re.match(input_re, k):
                target = re.sub(input_re, dest_path, k)
                result[target] = v
                break
    return result
