#!/usr/bin/env python
import argparse
import os
import yaml

from datadiff import diff
from getrels import parse_revs


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--summary', action='store_true')
    parser.add_argument('revs', nargs="+")
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
    return options, data


def summarize(a, b):
    print "{}\t{}\t{}\t{}".format(a['revision'][1:],
                                  len(a['interfaces']),
                                  len(a['relations']),
                                  b['revision'])
    services = set(a['interfaces'].keys()).symmetric_difference(
        set(b['interfaces'].keys()))

    services.update(set(a['relations'].keys()).symmetric_difference(
        set(b['relations'].keys())))

    if services:
        print ' '.join(sorted(services))


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
    options, data = setup()
    last = len(data) - 1
    for i, a in enumerate(data):
        if i + 1 > last:
            break
        b = data[i + 1]
        if options.summary:
            summarize(a, b)
        else:
            diffkey(a, b, 'interfaces')
            diffkey(a, b, 'relations')

    if len(data) > 2:
        summarize(data[0], data[-1])

if __name__ == '__main__':
    main()
