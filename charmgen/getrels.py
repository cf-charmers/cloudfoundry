#!/usr/bin/python

import argparse
import os
import re
import sys
import yaml

import git


JOBS_BLACKLIST = ['etcd', 'opentstb',
                  'ssl', 'smoke_tests',
                  'acceptance_tests', 'collector']
NAMESPACE_BLACKLIST = ['newrelic', 'packages', 'networks']


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory',
                        default=os.getcwd())
    parser.add_argument('revs', nargs="*")
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('-k', '--keep-defaults', action="store_true")

    options = parser.parse_args()
    find_jobs(options)
    return options


def find_jobs(options):
    basedir = options.directory
    if basedir.endswith('/'):
        basedir = basedir[:-1]
    if os.path.basename(basedir) == 'jobs':
        pass
    else:
        basedir = os.path.join(basedir, 'jobs')
        if os.path.isdir(basedir):
            options.directory = basedir
    options.directory = os.path.abspath(
        os.path.normpath(basedir))


def get_rev(repo, rev=None):
    refs = repo.references
    if rev:
        if isinstance(rev, int) and not str(rev).startswith('v'):
            rev = 'v%s' % rev
        try:
            return refs[rev]
        except IndexError:
            return None

    # find the max
    idx = 170   # we know we can start here
    ref = None
    while True:
        try:
            ref = refs['v%s' % idx]
            idx += 1
        except IndexError:
            return ref


def get_repo(basedir):
    repo = git.Repo(os.path.dirname(basedir))
    repo.remotes[0].update()
    return repo


def parse_revs(revs):
    result = []
    for rev in revs:
        match = re.search(r'v?(\d+)\.{2,3}v?(\d+)', rev)
        if match:
            start = int(match.group(1))
            lim = int(match.group(2))
            result.extend(range(start, lim + 1))
        else:
            result.append(rev)
    return result


def process_spec(job_name, spec_path, relations, interfaces, options):
    with open(spec_path) as fp:
        job_data = yaml.safe_load(fp)
        job_name = job_name.replace('-', '_')
        properties = job_data.get('properties')
        if not properties:
            return
        for prop, prop_data in properties.items():
            prop = prop.replace('-', '_')
            if '.' not in prop:
                ns = 'orchestrator'
                key = prop
            else:
                ns, key = prop.split('.', 1)

            if ns in NAMESPACE_BLACKLIST or ns in JOBS_BLACKLIST:
                continue

            # Skip keys with default values
            default = None
            if 'default' in prop_data:
                default = prop_data['default']

            if ns != job_name:
                relations.setdefault(job_name, set()).add(ns)
                relations.setdefault(ns, set()).add(job_name)

            if '.' in key:
                part = key.split('.', 1)[0]
                if part in NAMESPACE_BLACKLIST:
                    continue
            if options.keep_defaults is True or default is None:
                interfaces.setdefault(ns, {})[key] = default


def run_rev(repo, rev, options):
    ref = get_rev(repo, rev)
    if not ref:
        return
    repo.head.reference = ref
    repo.head.reset(index=True, working_tree=True)
    import pdb; pdb.set_trace()
    if options.verbose:
        print(ref.name)

    relations = {}
    interfaces = {}
    dirs = []
    for d in os.listdir(options.directory):
        d = os.path.join(options.directory, d)
        if os.path.isdir(d):
            dirs.append(d)
    summary = len(dirs)
    for d in dirs:
        job_name = os.path.basename(d)
        spec_path = os.path.join(d, 'spec')
        if not os.path.isfile(spec_path):
            continue
        if job_name in JOBS_BLACKLIST:
            continue
        process_spec(job_name, spec_path, relations, interfaces, options)

    # simplify relations
    for k, v in relations.items():
        relations[k] = sorted(v)

    with open('output-%s.yaml' % ref.name, 'w') as fp:
        yaml.safe_dump(
            dict(interfaces=interfaces,
                 relations=relations,
                 revision=ref.name),
            fp, default_flow_style=False)
    return summary


def main():
    options = setup()

    repo = get_repo(options.directory)
    revs = parse_revs(options.revs)
    if revs == []:
        revs = [None]
    summary = []
    for rev in revs:
        result = run_rev(repo, rev, options)
        if rev is not None and result is not None:
            summary.append([rev, result])

    yaml.safe_dump(summary, sys.stdout)


if __name__ == '__main__':
    main()
