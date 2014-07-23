import copy
import collections
import json
import os
import subprocess


def current_env():
    return subprocess.check_output(['juju', 'switch']).strip()


def record_pid():
    pid_dir = os.path.expanduser('~/.config/juju-deployer')
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    with open(os.path.join(pid_dir, 'server.pid'), 'w') as fp:
        fp.write('%s\n' % os.getpid())


def flatten_relations(rels):
    result = []
    for pair in rels:
        a = pair[0]
        b = pair[1]
        if isinstance(b, list):
            for ep in b:
                result.append(tuple(sorted((a, ep))))
        else:
            result.append(tuple(sorted((a, b))))
    return set(result)


def flatten_reality(real):
    result = set()
    for s, d in real['Services'].items():
        rels = d .get('Relations', {})
        for iface, reps in rels.items():
            for rep in reps:
                result.add(tuple(
                    sorted(('%s:%s' % (s, iface), rep))))
    return result


def rel_exists(reality, end_a, end_b):
    # Checks for a named relation on one side that matches the local
    # endpoint and remote service.
    (name_a, name_b, rem_a, rem_b) = (end_a, end_b, None, None)

    if ":" in end_a:
        name_a, rem_a = end_a.split(":", 1)
    if ":" in end_b:
        name_b, rem_b = end_b.split(":", 1)

    try:
        rels_svc_a = reality['Services'][name_a].get('Relations', {})

        found = False
        for r, related in rels_svc_a.items():
            if name_b in related:
                if rem_a and r not in rem_a:
                    continue
                found = True
                break
        if found:
            return True
    except KeyError:
        pass
    return False


def deepmerge(dest, src):
    """
    Deep merge of two dicts.

    This is destructive (`dest` is modified), but values
    from `src` are passed through `copy.deepcopy`.
    """
    for k, v in src.iteritems():
        if dest.get(k) and isinstance(v, dict):
            deepmerge(dest[k], v)
        else:
            dest[k] = copy.deepcopy(v)
    return dest


class NestedDict(dict):
    def __init__(self, dict_or_iterable=None, **kwargs):
        if dict_or_iterable:
            if isinstance(dict_or_iterable, dict):
                self.update(dict_or_iterable)
            elif isinstance(dict_or_iterable, collections.Iterable):
                for k, v in dict_or_iterable:
                    self[k] = v
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, key, value):
        key = key.split('.')
        o = self
        for part in key[:-1]:
            o = o.setdefault(part, {})
        dict.__setitem__(o, key[-1], value)

    def __getitem__(self, key):
        o = self
        if '.' in key:
            parts = key.split('.')
            key = parts[-1]
            for part in parts[:-1]:
                o = o[part]

        return dict.__getitem__(o, key)

    def update(self, other):
        deepmerge(self, other)


def parse_config(conf_fn, defaults=None):
    with open(conf_fn, 'r') as fp:
        conf = NestedDict()
        if defaults:
            conf.update(defaults)
        conf.update(json.load(fp))
        return conf
