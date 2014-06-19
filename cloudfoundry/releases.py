# The names of services in this file are references to
# services in cloudfoundry.services.SERVICES

COMMON_SERVICES = [
    ('cloud_controller_v1', 'cc'),
    ('router_v1', 'router'),
    ('nats_v1', 'nats'),
    ('dea_v1', 'dea'),
    ('uaa_v1', 'uaa'),
    ('logrouter_v1', 'logrouter'),
    ('loggregator_v1', 'loggregator'),
    ('hm9000_v1', 'hm'),

    ('cs:trusty/mysql', 'mysql'),
    ('cs:~hazmat/trusty/etcd', 'etcd'),
]

COMMON_RELATIONS = [
    (('cc', 'nats'), ('nats_v1', 'nats')),
    (("mysql", "db"), ('cc', "db"))
]

COMMON_UPGRADES = []


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
        "upgrades": COMMON_UPGRADES
    }
]
