#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import os
import sys
import shutil
from itertools import chain
import inspect

import pkg_resources
import yaml

try:
    from cloudfoundry import contexts
except ImportError:
    sys.path.append('.')
    from cloudfoundry import contexts


class CharmGenerator(object):
    author = "CloudFoundry Charm Generator <cs:~cf-charmers/cloudfoundry>"

    def __init__(self, releases, service_registry):
        self.__releases = releases
        self.release = None
        self.release_version = None
        self.service_registry = service_registry

    def select_release(self, version):
        if isinstance(version, str):
            try:
                version = int(version)
            except ValueError:
                raise KeyError(version)

        for r in self.__releases:
            versions = r['releases']
            low = versions[0]
            high = None
            if len(versions) == 2:
                high = versions[1]
            if version < low:
                continue
            if not high or version <= high:
                self.release = r
                self.release_version = version
                return r
        raise KeyError(version)

    def _is_relation(self, context):
        return inspect.isclass(context) and issubclass(context, contexts.RelationContext)

    def build_metadata(self, service_key):
        # service usage within the topo can include the service name
        # allowing this to be a tuple
        if isinstance(service_key, (tuple, list)):
            service_key = service_key[0]
        service = self.service_registry[service_key]
        result = dict(
            name=service_key,
            summary=service.get('summary', ''),
            description=service.get('description', ''),
            author=self.author,
            requires={
                contexts.OrchestratorRelation.name: dict(
                    interface=contexts.OrchestratorRelation.interface)
            })
        provides = {}
        for job in service.get('jobs', []):
            for relation in job.get('provided_data', []):
                if self._is_relation(relation):
                    provides[relation.name] = dict(interface=relation.interface)
            for relation in job.get('required_data', []):
                if self._is_relation(relation):
                    result['requires'][relation.name] = dict(
                        interface=relation.interface)
        if provides:
            result['provides'] = provides

        return result

    def build_hooks(self, service_key):
        meta = self.build_metadata(service_key)
        results = ['start', 'stop', 'config-changed',
                   'upgrade-charm', 'install']
        for rel in chain(meta.get('provides', {}), meta.get('requires', {})):
            results.append('{}-relation-changed'.format(rel))
            results.append('{}-relation-joined'.format(rel))
            results.append('{}-relation-broken'.format(rel))
        return results

    def build_entry(self, service_key):
        _, name, _ = self._parse_charm_ref(service_key)
        return "\n".join([
            '#!/usr/bin/env python2.7',
            'from cloudfoundry.jobs import job_manager',
            'job_manager("{}")'.format(name)
        ])

    def generate_charm(self, service_key, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        meta = self.build_metadata(service_key)
        meta_target = open(os.path.join(target_dir, 'metadata.yaml'), 'w')
        yaml.safe_dump(meta, meta_target, default_flow_style=False)
        meta_target.close()

        hook_dir = os.path.join(target_dir, 'hooks')
        if not os.path.exists(hook_dir):
            os.makedirs(hook_dir)
        entry = os.path.join(target_dir, 'hooks', 'entry.py')

        with open(entry, 'w') as target:
            os.fchmod(target.fileno(), 0755)
            target.write(self.build_entry(service_key))

        for hook in self.build_hooks(service_key):
            os.symlink(entry, os.path.join(hook_dir, hook))

    def _build_charm_ref(self, charm_id):
        if charm_id.startswith('cs:'):
            return dict(charm=charm_id)
        else:
            return dict(
                charm=charm_id,
                branch="local:trusty/{}".format(charm_id)
            )

    def _parse_charm_ref(self, service_id):
        if isinstance(service_id, tuple):
            charm_id = charm_name = service_id[0]
            service_name = service_id[1]
        else:
            charm_id = charm_name = service_id
            service_name = service_id

        if '/' in charm_name:
            charm_name = charm_name.split('/', 1)[1]

        if '/' in service_name:
            service_name = service_name.split('/', 1)[1]
        return charm_id, charm_name, service_name

    def _normalize_relation(self, rel):
        if isinstance(rel, tuple):
            return "{}:{}".format(*rel)
        else:
            return rel

    def _get_managed_charms(self):
        charms = []
        for service in self.release['topology']['services']:
            charm_id, charm_name, service_name = self._parse_charm_ref(service)
            if charm_id.startswith('cs:'):
                continue
            if charm_name not in self.service_registry:
                raise KeyError(
                    'Missing service_registry definition for charm: {}'.format(
                        charm_name))
            charms.append((charm_id, charm_name, service_name))
        return charms

    def _get_relations(self):
        relations = self.release['topology'].get('relations', [])
        services = {service_name: self.service_registry[charm_name]
                    for _, charm_name, service_name in self._get_managed_charms()}
        provided = {provider.name: service_name
                    for service_name, service_def in services.iteritems()
                    for job in service_def.get('jobs', [])
                    for provider in job.get('provided_data', [])}
        for service_name, service_def in services.iteritems():
            for job in service_def.get('jobs', []):
                for required in job.get('required_data', []):
                    if not self._is_relation(required):
                        continue
                    if not required.name in provided:
                        continue
                    provider_name = provided[required.name]
                    lhs = (service_name, required.name)
                    rhs = (provider_name, required.name)
                    relations.append((lhs, rhs))
        return relations

    def build_deployment(self):
        services = {}
        relations = []
        result = {'cloudfoundry': {
            # Trusty is Magic!
            'series': 'trusty',
            'services': services,
            'relations': relations
        }}

        rel_data = {}
        for service_id in self.release['topology']['services']:
            charm_id, _, service_name = self._parse_charm_ref(service_id)
            services[service_name] = self._build_charm_ref(charm_id)

        for rel in self._get_relations():
            lhs = self._normalize_relation(rel[0])
            rhs = self._normalize_relation(rel[1])
            rel_data.setdefault(lhs, []).append(rhs)
        for k, v in rel_data.items():
            relations.append((k, tuple(v)))
        return result

    def generate_deployment(self, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        bundle = self.build_deployment()
        target = os.path.join(target_dir, 'bundles.yaml')
        with open(target, 'w') as fp:
            yaml.safe_dump(bundle, fp, default_flow_style=False)
            fp.flush()

    def generate(self, target_dir):
        # Ensure that both the target dir
        # and its 'trusty' subdir exists
        repo = os.path.join(target_dir, 'trusty')
        if not os.path.exists(repo):
            os.makedirs(repo)
        self.generate_deployment(target_dir)

        for _, charm_name, _ in self._get_managed_charms():
            charm_path = os.path.join(repo, charm_name)
            if not os.path.exists(charm_path):
                os.makedirs(charm_path)

            self.generate_charm(charm_name, charm_path)
            shutil.copytree(pkg_resources.resource_filename(
                __name__, '../cloudfoundry'),
                os.path.join(charm_path, 'hooks', 'cloudfoundry'))
            shutil.copytree(pkg_resources.resource_filename(
                __name__, '../files'),
                os.path.join(charm_path, 'files'))
            # copy charmhelpers into the hook_dir
            shutil.copytree(pkg_resources.resource_filename(
                __name__, '../hooks/charmhelpers'),
                os.path.join(charm_path, 'hooks', 'charmhelpers'))


def main(args=None):
    from cloudfoundry.releases import RELEASES
    from cloudfoundry.services import SERVICES
    parser = argparse.ArgumentParser()
    parser.add_argument('release', type=int)
    parser.add_argument('-d', '--directory', dest="directory")
    parser.add_argument('-f', '--force', action="store_true")
    options = parser.parse_args(args)

    using_default_dir = False
    if not options.directory:
        options.directory = "cloudfoundry-r{}".format(options.release)
        using_default_dir = True
    if not os.path.exists(options.directory):
        os.mkdir(options.directory)
    else:
        if options.force:
            shutil.rmtree(options.directory)
            os.mkdir(options.directory)
        elif using_default_dir is True:
            raise SystemExit("Release already generated: {}".format(
                options.directory))

    g = CharmGenerator(RELEASES, SERVICES)
    g.select_release(options.release)
    g.generate(options.directory)

if __name__ == '__main__':
    main()
