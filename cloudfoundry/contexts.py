import os
import re
import subprocess
import yaml

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core.services import RelationContext
from cloudfoundry.releases import RELEASES


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
                    address=hookenv.unit_get(
                        'private-address').encode('utf-8'))

    def erb_mapping(self):
        data = self[self.name]
        return {
            'nats.machines': [u['address'] for u in data],
            'nats.port': data[0]['port'],
            'nats.user': data[0]['user'],
            'nats.password': data[0]['password'],
        }


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


class ClockRelation(RelationContext):
    name = 'clock'
    interface = 'clock'
    required_keys = []


class UAARelation(RelationContext):
    name = 'uaa'
    interface = 'http'
    required_keys = []


class SyslogAggregatorRelation(RelationContext):
    name = 'syslog_aggregator'
    interface = 'syslog_aggregator'
    required_keys = ['address', 'port', 'transport', 'all']

    def provide_data(self):
        return {}


class LoginRelation(RelationContext):
    name = 'login'
    interface = 'http'
    required_keys = []


class DEARelation(RelationContext):
    name = 'dea'
    interface = 'dea'
    required_keys = []


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


class LTCRelation(RelationContext):
    name = 'ltc'
    interface = 'loggregator_trafficcontroller'
    required_keys = ['shared_secret', 'host', 'port', 'outgoing_port'],
    outgoing_port = 8083
    port = 8882

    def get_shared_secret(self):
        secret_context = StoredContext(
            os.path.join(hookenv.charm_dir(), '.ltc-secret.yml'),
            {'shared_secret': host.pwgen(20)})
        return secret_context['shared_secret']

    def provide_data(self):
        return {
            'host': hookenv.unit_get('private-address').encode('utf-8'),
            'port': self.port,
            'outgoing_port': self.outgoing_port,
            'shared_secret': self.get_shared_secret(),
        }

    def erb_mapping(self):
        data = self[self.name]
        return {
            'loggregator_endpoint.host': data[0]['address'],
            'loggregator_endpoint.port': data[0]['incoming_port'],
            'loggregator_endpoint.shared_secret': data[0]['shared_secret'],
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

    def erb_mapping(self):
        data = self[self.name]
        return {
            'loggregator.servers': [d['address'] for d in data],
            'loggregator.incoming_port': data[0]['incoming_port'],
            'loggregator.outgoing_port': data[0]['outgoing_port'],
        }


class EtcdRelation(RelationContext):
    name = 'etcd'
    interface = 'etcd'
    required_keys = ['hostname', 'port']

    def erb_mapping(self):
        data = self[self.name]
        return {
            'etcd.machines': [d['hostname'] for d in data],
        }


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

    def erb_mapping(self):
        data = self[self.name]
        return {
            'cc.srv_api_url': data[0]['hostname'],  # TODO: Probably needs to be an actual URL
            'cc.srv_api_user': data[0]['user'],
            'cc.srv_api_password': data[0]['password'],
        }


class OrchestratorRelation(RelationContext):
    name = "orchestrator"
    interface = "orchestrator"
    required_keys = ['artifacts_url', 'cf_version', 'domain']

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

    def provide_data(self):
        config = hookenv.config()
        private_addr = hookenv.unit_private_ip()
        version = config['cf_version']
        if version == 'latest':
            version = RELEASES[0]['releases'][1]
        return {
            'artifacts_url': 'http://{}:8019'.format(private_addr),  # FIXME: this should use SSL
            'cf_version': version,
            'domain': self.get_domain(),
        }

    def erb_mapping(self):
        return {
            'router.domain': self[self.name][0]['domain'],
        }


class JujuAPICredentials(dict):
    def __init__(self):
        super(JujuAPICredentials, self).__init__()
        config = hookenv.config()
        if config.get('admin_secret'):
            self['api_address'] = 'wss://{}'.format(self.get_api_address())
            self['api_password'] = config['admin_secret']

    def get_api_address(self, unit_dir=None):
        """Return the Juju API address.

        (Copied from lp:~juju-gui/charms/trusty/juju-gui/trunk)
        """
        api_addresses = os.getenv('JUJU_API_ADDRESSES')
        if api_addresses is not None:
            return api_addresses.split()[0]
        # The JUJU_API_ADDRESSES environment variable is not included in the hooks
        # context in older releases of juju-core.  Retrieve it from the machiner
        # agent file instead.
        if unit_dir is None:
            base_dir = os.path.join(hookenv.charm_dir(), '..', '..')
        else:
            base_dir = os.path.join(unit_dir, '..')
        base_dir = os.path.abspath(base_dir)
        for dirname in os.listdir(base_dir):
            if dirname.startswith('machine-'):
                agent_conf = os.path.join(base_dir, dirname, 'agent.conf')
                break
        else:
            raise IOError('Juju agent configuration file not found.')
        contents = yaml.load(open(agent_conf))
        return contents['apiinfo']['addrs'][0]


class ArtifactsCache(dict):
    def __init__(self):
        config = hookenv.config()
        if config.get('artifacts_url'):
            self.update({
                'artifacts_url': config['artifacts_url'],
            })
