import os
import pkg_resources
import yaml

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
    interface = 'nats'
    required_keys = ['address', 'port', 'user', 'password']


class MysqlRelation(RelationContext):
    interface = 'db'
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
    interface = 'router'
    required_keys = ['domain']


class LogRouterRelation(RelationContext):
    interface = 'logrouter'
    required_keys = ['shared_secret', 'address', 'incoming_port', 'outgoing_port']


class LoggregatorRelation(RelationContext):
    interface = 'loggregator'
    required_keys = ['address', 'incoming_port', 'outgoing_port']


class EtcdRelation(RelationContext):
    interface = 'etcd'
    required_keys = ['hostname', 'port']


class CloudControllerRelation(RelationContext):
    interface = 'cc'
    required_keys = ['hostname', 'port', 'user', 'password']

class OrchestratorRelation(RelationContext):
    name = "orchestrator"
    interface = "orchestrator"

    @property
    def required_keys(self):
        config_yaml = pkg_resources.resource_filename(__name__,
                                                      '../config.yaml')
        config = yaml.safe_load(open(config_yaml))
        return [option for option in config['options']]
