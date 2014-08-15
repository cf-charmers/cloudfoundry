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
        if not os.path.isabs(file_name):
            file_name = os.path.join(hookenv.charm_dir(), file_name)
        with open(file_name, 'w') as file_stream:
            os.fchmod(file_stream.fileno(), 0600)
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
    port = 4222

    def get_credentials(self):
        return StoredContext('nats_credentials.yml', {
            'user': host.pwgen(7),
            'password': host.pwgen(7),
        })

    def provide_data(self):
        return dict(
            self.get_credentials(),
            port=self.port,
            address=hookenv.unit_get('private-address').encode('utf-8'))

    def erb_mapping(self):
        data = self[self.name]
        return {
            'nats.machines': [u['address'] for u in data],
            'nats.address': data[0]['address'],
            'nats.port': int(data[0]['port']),
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
    required_keys = ['login_client_secret', 'admin_client_secret', 'cc_client_secret', 'cc_token_secret',
                     'service_broker_client_secret', 'servicesmgmt_client_secret', 'port']
    port = 8081

    def get_shared_secrets(self):
        secret_context = StoredContext('uaa-secrets.yml', {
            'login_client_secret': host.pwgen(20),
            'admin_client_secret': host.pwgen(20),
            'cc_client_secret': host.pwgen(20),
            'cc_token_secret': host.pwgen(20),
            'service_broker_client_secret': host.pwgen(20),
            'servicesmgmt_client_secret': host.pwgen(20),
        })
        return secret_context

    def provide_data(self):
        return dict({
            'port': self.port,
        }, **self.get_shared_secrets())

    def erb_mapping(self):
        data = self[self.name][0]
        return {
            'uaa.login.client_secret': data['login_client_secret'],
            'uaa.admin.client_secret': data['admin_client_secret'],
            'uaa.cc.client_secret': data['cc_client_secret'],
            'uaa.cc.token_secret': data['cc_token_secret'],
            'uaa.port': data['port'],
            'uaa.require_https': False,  # FIXME: Add SSL as an option; requires cert
            'uaa.no_ssl': True,
            'uaa.scim.users': [
                'admin|admin|scim.write,scim.read,openid,cloud_controller.admin',  # FIXME: Don't hard-code
            ],
            'uaa.clients': {
                'cc_service_broker_client': {
                    'secret': data['service_broker_client_secret'],
                    'scope': 'openid,cloud_controller_service_permissions.read',
                    'authorities': 'clients.read,clients.write,clients.admin',
                    'authorized-grant-types': 'client_credentials',
                },
                'servicesmgmt': {
                    'authorities': 'uaa.resource,oauth.service,clients.read,clients.write,clients.secret',
                    'authorized-grant-types': 'authorization_code,client_credentials,password,implicit',
                    'autoapprove': True,
                    'override': True,
                    'redirect-uri': 'http://servicesmgmt.10.244.0.34.xip.io/auth/cloudfoundry/callback',
                    'scope': 'openid,cloud_controller.read,cloud_controller.write',
                    'secret': data['servicesmgmt_client_secret'],
                },
            },
        }


class LoginRelation(RelationContext):
    name = 'login'
    interface = 'http'
    required_keys = []
    port = 8080

    def provide_data(self):
        return {
            'port': self.port,
        }

    def erb_mapping(self):
        data = self[self.name][0]
        return {
            'login.port': data['port'],
        }


class DEARelation(RelationContext):
    name = 'dea'
    interface = 'dea'
    required_keys = []

    def erb_mapping(self):
        return {
            'dea_next.directory_server_protocol': 'http',
        }


class LTCRelation(RelationContext):
    name = 'ltc'
    interface = 'loggregator_trafficcontroller'
    required_keys = ['shared_secret', 'host', 'port', 'outgoing_port']
    incoming_port = 3456
    outgoing_port = 8082

    def get_shared_secret(self):
        secret_context = StoredContext('ltc-secrets.yml', {
            'shared_secret': host.pwgen(20),
        })
        return secret_context['shared_secret']

    def provide_data(self):
        return {
            'host': hookenv.unit_get('private-address').encode('utf-8'),
            'port': self.incoming_port,
            'outgoing_port': self.outgoing_port,
            'shared_secret': self.get_shared_secret(),
        }

    def erb_mapping(self):
        data = self[self.name]
        return {
            'loggregator_endpoint.host': data[0]['host'],
            'loggregator_endpoint.port': data[0]['port'],
            'loggregator_endpoint.shared_secret': data[0]['shared_secret'],
            'traffic_controller.zone': 'z1',
            'traffic_controller.host': data[0]['host'],
            'traffic_controller.incoming_port': data[0]['port'],
            'traffic_controller.outgoing_port': data[0]['outgoing_port'],
            'logger_endpoint.use_ssl': False,  # TODO: support SSL option
            'logger_endpoint.port': 80,  # default is 443
        }


class LoggregatorRelation(RelationContext):
    name = 'loggregator'
    interface = 'loggregator'
    required_keys = ['address', 'incoming_port', 'outgoing_port']
    incoming_port = 3457
    outgoing_port = 8083

    def provide_data(self):
        return {
            'address': hookenv.unit_get('private-address').encode('utf-8'),
            'incoming_port': self.incoming_port,
            'outgoing_port': self.outgoing_port,
        }

    def erb_mapping(self):
        data = self[self.name]
        return {
            'loggregator.zone': 'z1',
            'loggregator.servers': {'z1': [d['address'] for d in data]},
            'loggregator.incoming_port': data[0]['incoming_port'],
            'loggregator.outgoing_port': data[0]['outgoing_port'],
        }


class EtcdRelation(RelationContext):
    name = 'etcd'
    interface = 'http'
    required_keys = ['hostname', 'port']

    def erb_mapping(self):
        data = self[self.name]
        return {
            'etcd.machines': [d['hostname'] for d in data],
        }


class CloudControllerRelation(RelationContext):
    name = 'cc'
    interface = 'controller'
    required_keys = ['hostname', 'port', 'user', 'password', 'db_encryption_key']

    def get_credentials(self):
        return StoredContext('api_credentials.yml', {
            'user': host.pwgen(7),
            'password': host.pwgen(7),
            'db_encryption_key': host.pwgen(7),
        })

    def provide_data(self):
        creds = self.get_credentials()
        return {
            'user': creds['user'],
            'password': creds['password'],
            'db_encryption_key': creds['db_encryption_key'],
            'hostname': hookenv.unit_get('private-address').encode('utf-8'),
            'port': 9022,
        }

    def erb_mapping(self):
        data = self[self.name][0]
        return {
            # TODO: Can the API URI support SSL?  Maybe use the public endpoint?
            'cc.srv_api_uri': 'http://{}:{}'.format(data['hostname'], data['port']),
            'cc.bulk_api_user': data['user'],
            'cc.bulk_api_password': data['password'],
            'cc.staging_upload_user': 'ignored',  # FIXME: We need a staging cache set up
            'cc.staging_upload_password': 'ignored',
            'cc.db_encryption_key': data['db_encryption_key'],
            'cc.quota_definitions': {
                'default': {
                    'memory_limit': 10240,
                    'non_basic_services_allowed': True,
                    'total_routes': 1000,
                    'total_services': 100,
                    'trial_db_allowed': True,
                },
            },
            'cc.install_buildpacks': [  # FIXME: This should be dynamic or versioned
                {'name': 'java_buildpack', 'package': 'buildpack_java_offline'},
                {'name': 'ruby_buildpack', 'package': 'buildpack_ruby'},
                {'name': 'nodejs_buildpack', 'package': 'buildpack_nodejs'},
                {'name': 'go_buildpack', 'package': 'buildpack_go'},
                {'name': 'python_buildpack', 'package': 'buildpack_python'},
                {'name': 'php_buildpack', 'package': 'buildpack_php'},
            ],
            'cc.security_group_definitions': [
                {'name': 'public_networks',
                 'rules': [
                     {'protocol': 'all',
                      'destination': '0.0.0.0-9.255.255.255'},
                     {'protocol': 'all',
                      'destination': '11.0.0.0-169.253.255.255'},
                     {'protocol': 'all',
                      'destination': '169.255.0.0-172.15.255.255'},
                     {'protocol': 'all',
                      'destination': '172.32.0.0-192.167.255.255'},
                     {'protocol': 'all',
                      'destination': '192.169.0.0-255.255.255.255'},
                 ]},
                {'name': 'dns',
                 'rules': [
                     {'protocol': 'tcp',
                      'destination': '0.0.0.0/0',
                      'ports': '53'},
                     {'protocol': 'udp',
                      'destination': '0.0.0.0/0',
                      'ports': '53'},
                 ]},
            ],
            'cc.default_running_security_groups': ['public_networks', 'dns'],
            'cc.default_staging_security_groups': ['public_networks', 'dns'],
        }


class CloudControllerDBRelation(RelationContext):
    name = 'cc-db'
    interface = 'controller-db'
    required_keys = MysqlRelation.required_keys

    @classmethod
    def send_data(cls, job_name):
        # using send_data instead of provide_data to delay it until data_ready
        data = MysqlRelation()['db'][0]
        for rid in hookenv.relation_ids(cls.name):
            hookenv.relation_set(rid, data)


class RouterRelation(RelationContext):
    name = 'router'
    interface = 'http'
    required_keys = ['address']
    port = 80
    varz_port = 8084  # not currently used

    def provide_data(self):
        return {
            'address': hookenv.unit_get('private-address').encode('utf-8'),
            'port': self.port,
        }

    def erb_mapping(self):
        return {
            'router.servers.z1': [u['address'] for u in self[self.name]],
            'router.servers.z2': [],
            'router.port': self.port,
        }


class OrchestratorRelation(RelationContext):
    name = "orchestrator"
    interface = "orchestrator"
    required_keys = ['artifacts_url', 'cf_version', 'domain']

    def get_domain(self):
        # must be here, because deployer is only installed on cloudfoundry
        from cloudfoundry.api import APIEnvironment
        domain = hookenv.config()['domain']
        if domain == 'xip.io':
            creds = JujuAPICredentials()
            if not creds:
                return domain
            env = APIEnvironment(creds['api_address'], creds['api_password'])
            env.connect()
            status = env.status()
            if 'haproxy' in status['services']:
                units = status['services']['haproxy']['units']
                unit0 = sorted(units.items(), key=lambda a: a[0])[0][1]
                public_address = unit0['public-address']
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
        domain = self[self.name][0]['domain']
        return {
            'domain': domain,
            'app_domains': [d['domain'] for d in self[self.name]],
            'system_domain': domain,  # TODO: These should probably be config options
            'system_domain_organization': 'juju-org',
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
