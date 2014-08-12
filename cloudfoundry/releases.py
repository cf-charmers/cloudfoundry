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
    ('dea-v1', 'dea'),
    ('login-v1', 'login'),
    ('nats-stream-forwarder-v1', 'nats-sf'),
    ('loggregator-v1', 'loggregator'),
    ('loggregator-trafficcontroller-v1', 'loggregator-trafficcontrol'),
    ('hm9000-v1', 'hm'),
    ('haproxy-v1', 'haproxy'),

    ('cs:trusty/mysql', 'mysql'),
    ('cs:~hazmat/trusty/etcd', 'etcd'),
]

# These map service name:interface pairs to become deployment relations
# for a given topo.  These are supplemented by relations generated from
# the services lists; these are mainly for specifying relations for
# unmanaged (charm store) charms.
COMMON_RELATIONS = [
    ('mysql:db', 'cc:db'),
    ('mysql:db', 'uaa:db'),
    ('etcd:client', 'hm:etcd'),
    ('etcd:client', 'loggregator:etcd'),
    ('etcd:client', 'loggregator-trafficcontrol:etcd'),
]

COMMON_UPGRADES = []


RELEASES = [
    {
        "releases": (173, 176),
        "topology": {
            "services": COMMON_SERVICES,
            "relations": COMMON_RELATIONS,
            "expose": ['haproxy'],
            "constraints": {
                "__default__": "arch=amd64",
                "cc": "arch=amd64 root-disk=12G mem=12G",
                "cc-worker": "arch=amd64 root-disk=10G",
                "cc-clock": "arch=amd64 root-disk=10G",
                "dea": "arch=amd64 mem=5G",
            },
        },
        "upgrades": COMMON_UPGRADES
    }
]
