#!/usr/bin/python

import argparse
import os
import re
import yaml

import git


JOBS_BLACKLIST = ['etcd', 'networks', 'opentstb',
                  'ssl', 'uaadb', 'smoke_tests',
                  'databases']


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory',
                        default=os.getcwd())
    parser.add_argument('-r', '--revs')

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
    repo.remotes[0].fetch()
    return repo


def parse_revs(revs):
    match = re.search(r'v?(\d+)\.{2,3}v?(\d+)', revs)
    if match:
        start = int(match.group(1))
        lim = int(match.group(2))
        revs = range(start, lim + 1)
    else:
        revs = [revs]
    return revs


def process_spec(job_name, spec_path, relations, interfaces):
    with open(spec_path) as fp:
        job_data = yaml.safe_load(fp)
        job_name = job_name.replace('-', '_')
        properties = job_data.get('properties')
        if not properties:
            return
        for prop, prop_data in properties.items():
            prop = prop.replace('-', '_')
            if '.' not in prop:
                ns = 'implicit'
                key = prop
            else:
                ns, key = prop.split('.', 1)
            if ns in JOBS_BLACKLIST:
                continue

            if 'default' in prop_data:
                continue

            relations.setdefault(ns, set()).add(job_name)

            if '.' in key:
                remote = key.split('.', 1)[0]
                remote = remote.replace('-', '_')
                if remote == job_name or remote in JOBS_BLACKLIST:
                    continue
                interfaces.setdefault(job_name, set()).add(remote)


def run_rev(repo, rev, options):
    ref = get_rev(repo, rev)
    if not ref:
        return
    repo.head.reference = ref
    repo.head.reset(index=True, working_tree=True)
    print ref.name

    relations = {}
    interfaces = {}
    dirs = []
    for d in os.listdir(options.directory):
        d = os.path.join(options.directory, d)
        if os.path.isdir(d):
            dirs.append(d)
    for d in dirs:
        job_name = os.path.basename(d)
        spec_path = os.path.join(d, 'spec')
        if not os.path.isfile(spec_path):
            continue
        if job_name in JOBS_BLACKLIST:
            continue
        process_spec(job_name, spec_path, relations, interfaces)

    with open('output-%s.yaml' % ref.name, 'w') as fp:
        yaml.safe_dump(
            dict(interfaces=interfaces,
                 relations=relations,
                 revision=ref.name),
            fp)


def main():
    options = setup()

    repo = get_repo(options.directory)
    revs = parse_revs(options.revs)
    for rev in revs:
        run_rev(repo, rev, options)


if __name__ == '__main__':
    main()
