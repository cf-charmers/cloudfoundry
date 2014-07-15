# The names of services in this file are references to
# services in cloudfoundry.services.SERVICES

# Service Definition to deployed service name
# mapping
COMMON_SERVICES = [
    ('cloud-controller-v1', 'cc'),
    ('cloud-controller-clock-v1', 'cc-clock'),
    ('cloud-controller-worker-v1', 'cc-worker'),
    ('router-v1', 'router'),
    ('nats-v1', 'nats'),
    ('uaa-v1', 'uaa'),
    #('dea-v1', 'dea'),
    #('login-v1', 'login'),
    #('dea-logging-agent-v1', 'dea-logging'),
    #('nats-stream-forwarder', 'nats-sf'),
    #('loggregator-v1', 'loggregator'),
    #('loggregator-trafficcontrol-v1', 'loggregator-trafficcontrol'),
    #('hm9000-v1', 'hm'),
    #('syslog-aggregator-v1', 'syslog-aggregator'),
    #('haproxy-v1', 'haproxy')

    ('cs:trusty/mysql', 'mysql'),
    ('cs:~hazmat/trusty/etcd', 'etcd'),
]

# These map service name:interface pairs
# to become deployment relations for a given topo.
COMMON_RELATIONS = [
    ('nats:nats', 'router:nats'),
    ('uaa:db', 'mysql:db')
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
