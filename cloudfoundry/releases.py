# The names of services in this file are references to
# services in cloudfoundry.services.SERVICES

# Service Definition to deployed service name
# mapping
COMMON_SERVICES = [
    ('cloud-controller-v1', 'cc'),
    ('router-v1', 'router'),
    ('nats-v1', 'nats'),
    #('dea-v1', 'dea'),
    #('uaa-v1', 'uaa'),
    #('logrouter-v1', 'logrouter'),
    #('loggregator-v1', 'loggregator'),
    #('hm9000-v1', 'hm'),

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
