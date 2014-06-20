import re
import os
import yaml
import subprocess

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core.services import RelationContext


class StoredContext(dict):
    """
    A data context that always returns the data that it was first created with.
    """
    def __init__(self, file_name, config_data):
        """
        If the file exists, populate `self` with the data from the file.
        Otherwise, populate with the given data and persist it to the file.
        """
        if os.path.exists(file_name):
            self.update(self.read_context(file_name))
        else:
            self.store_context(file_name, config_data)
            self.update(config_data)

    def store_context(self, file_name, config_data):
        with open(file_name, 'w') as file_stream:
            yaml.dump(config_data, file_stream)

    def read_context(self, file_name):
        with open(file_name, 'r') as file_stream:
            data = yaml.load(file_stream)
            if not data:
                raise OSError("%s is empty" % file_name)
            return data


class NatsRelation(RelationContext):
    name = 'nats'
    interface = 'nats'
    required_keys = ['address', 'port', 'user', 'password']

    def get_credentials(self):
        return StoredContext(
            'nats_credentials.yml', {
                'user': host.pwgen(7),
                'password': host.pwgen(7),
            })

    def provide_data(self):
        return dict(self.get_credentials(),
                    port=4222,
                    address=hookenv.unit_get('private-address').encode('utf-8'))


class MysqlRelation(RelationContext):
    name = 'db'
    interface = 'mysql'
    required_keys = ['user', 'password', 'host', 'database']
    dsn_template = "mysql2://{user}:{password}@{host}:{port}/{database}"

    def get_data(self):
        RelationContext.get_data(self)
        if self.is_ready():
            for unit in self['db']:
                if 'port' not in unit:
                    unit['port'] = '3306'
                unit['dsn'] = self.dsn_template.format(**unit)


class RouterRelation(RelationContext):
    name = 'router'
    interface = 'router'
    required_keys = ['domain']

    def provide_data(self):
        return {'domain': self.get_domain()}

    def get_domain(self):
        domain = hookenv.config()['domain']
        if domain == 'xip.io':
            public_address = hookenv.unit_get('public-address')
            domain = "%s.xip.io" % self.to_ip(public_address)
        return domain

    def to_ip(self, address):
        ip_pat = re.compile('^(\d{1,3}\.){3}\d{1,3}$')
        if ip_pat.match(address):
            return address  # already an IP
        else:
            result = subprocess.check_output(
                ['dig', '+short', '@8.8.8.8', address])
            for candidate in result.split('\n'):
                candidate = candidate.strip()
                if ip_pat.match(candidate):
                    return candidate
            return None


class LogRouterRelation(RelationContext):
    name = 'logrouter'
    interface = 'logrouter'
    required_keys = ['shared_secret', 'address', 'incoming_port', 'outgoing_port']
    incoming_port = 3456
    outgoing_port = 8083
    varz_port = 8882

    def get_shared_secret(self):
        secret_context = StoredContext(
            os.path.join(hookenv.charm_dir(), '.logrouter-secret.yml'),
            {'shared_secret': host.pwgen(20)})
        return secret_context['shared_secret']

    def provide_data(self):
        return {
            'address': hookenv.unit_get('private-address').encode('utf-8'),
            'incoming_port': self.incoming_port,
            'outgoing_port': self.outgoing_port,
            'shared_secret': self.get_shared_secret(),
        }


class LoggregatorRelation(RelationContext):
    name = 'loggregator'
    interface = 'loggregator'
    required_keys = ['address', 'incoming_port', 'outgoing_port']
    incoming_port = 3457
    outgoing_port = 8082
    varz_port = 8883

    def provide_data(self):
        return {
            'address': hookenv.unit_get('private-address').encode('utf-8'),
            'incoming_port': self.incoming_port,
            'outgoing_port': self.outgoing_port,
        }


class EtcdRelation(RelationContext):
    name = 'etcd'
    interface = 'etcd'
    required_keys = ['hostname', 'port']


class CloudControllerRelation(RelationContext):
    name = 'cc'
    interface = 'controller'
    required_keys = ['hostname', 'port', 'user', 'password']

    def get_credentials(self):
        return StoredContext('api_credentials.yml', {
            'user': host.pwgen(7),
            'password': host.pwgen(7),
        })

    def provide_data(self):
        return dict(self.get_credentials(),
                    hostname=hookenv.unit_get('private-address').encode('utf-8'),
                    port=9022)
