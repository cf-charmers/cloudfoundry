import pkg_resources
import yaml

from charmhelpers.core.services import RelationContext


class OrchestratorRelation(RelationContext):
    name = "orchestrator"
    interface = "orchestrator"

    @property
    def required_keys(self):
        config_yaml = pkg_resources.resource_filename(__name__,
                                                      '../config.yaml')
        config = yaml.safe_load(open(config_yaml))
        return [option for option in config['options']]
