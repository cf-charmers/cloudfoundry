#!/usr/bin/env python
import argparse
import os
import yaml

from datadiff import diff
from getrels import parse_revs


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('revs')
    options = parser.parse_args()

    data = []
    revs = map(str, parse_revs(options.revs))
    for r in revs:
        if not os.path.exists(r):
            if not r.startswith('v'):
                r = 'output-v%s.yaml' % r
                if not os.path.exists(r):
                    continue

        with open(r) as fp:
            data.append(yaml.safe_load(fp))
    return data


def diffkey(a, b, key=None):
    if key:
        aa = a[key]
        bb = b[key]
    else:
        aa = a
        bb = b
    output = diff(aa, bb, context=1,
                  fromfile=a['revision'] + '-' + key,
                  tofile=b['revision'] + '-' + key)
    if output:
        show = False
        for line in output.stringify(include_preamble=False):
            if line.startswith('-') or line.startswith('+'):
                show = True
                break
        if not show:
            return
        print output


def main():
    data = setup()
    last = len(data) - 1
    for i, a in enumerate(data):
        if i + 1 > last:
            break
        b = data[i + 1]
        diffkey(a, b, 'interfaces')
        diffkey(a, b, 'relations')

if __name__ == '__main__':
    main()
