from cloudfoundry import contexts
from cloudfoundry import tasks
from cloudfoundry import utils


leader_elected_cc_migration = lambda x: None
leader_elected_uaa_migration = lambda x: None
deploy_cc_clock = lambda x: None

job_templates = lambda x: None
db_migrate = lambda x: None


SERVICES = {
    'cc_clock_v1': {},
    'cloud_controller_v1': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [{
            'job_name': 'cf-cloudcontroller-ng',
            'mapping': {
                # process the final context before feeding it to erb render
                # using this rel_key to property path mapping
            },
            'install': [utils.apt_install(['linux-image-extras']),
                        utils.modprobe(['quota_v1', 'quota_v2'])],
            "provided_data": [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.MysqlRelation,
                              # contexts.BundleConfig,
                              # All job context keys
                              # get processed by a name mapper
                              ],
            'data_ready': [job_templates, db_migrate, ],
        }]
    },
    'nats_v1': {},
    'router_v1': {}
}


COMMON_SERVICES = [
    ('cloud_controller_v1', 'cc'), "cs:trusty/mysql", 'router_v1'
]

COMMON_RELATIONS = [
    (('cc', 'nats'), ('nats_v1', 'nats')),
    (("mysql", "db"), ('cc', "db"))
]

COMMON_UPGRADES = [
    leader_elected_cc_migration,
    leader_elected_uaa_migration,
]


RELEASES = [
    {
        "releases": (173,),
        "topology": {
            "services": COMMON_SERVICES + ['cc_clock_v1'],
            "expose": ['router_v1'],
            "relations": COMMON_RELATIONS + [
                (('cc', 'clock'), ('cc_clock_v1', 'clock'))
            ]
        },
        "upgrades": COMMON_UPGRADES + [deploy_cc_clock]
    },

    {
        "releases": (171, 172),
        "topology": {
            "services": COMMON_SERVICES,
            "expose": ['router_v1'],
            "relations": COMMON_RELATIONS,
        },
        "upgrades": COMMON_UPGRADES
    }
]
