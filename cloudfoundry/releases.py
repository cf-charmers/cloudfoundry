# The names of services in this file are references to
# services in cloudfoundry.services.SERVICES

# Service Definition to deployed service name
# mapping
COMMON_SERVICES = [
    ('cloud_controller_v1', 'cc'),
    ('router_v1', 'router'),
    ('nats_v1', 'nats'),
    #('dea_v1', 'dea'),
    #('uaa_v1', 'uaa'),
    #('logrouter_v1', 'logrouter'),
    #('loggregator_v1', 'loggregator'),
    #('hm9000_v1', 'hm'),

    ('cs:trusty/mysql', 'mysql'),
    ('cs:~hazmat/trusty/etcd', 'etcd'),
]

# These map service name:interface pairs
# to become deployment relations for a given topo.
COMMON_RELATIONS = [
    ('nats:nats', 'router:nats'),
]

COMMON_UPGRADES = []


RELEASES = [
    {
        "releases": (173, 173),
        "topology": {
            "services": COMMON_SERVICES,
            "expose": ['router_v1'],
            "relations": COMMON_RELATIONS
        },
        "upgrades": COMMON_UPGRADES
    }
]
