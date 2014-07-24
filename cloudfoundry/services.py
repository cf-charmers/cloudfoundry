import contexts
import mapper

__all__ = ['SERVICES']

SERVICES = {
    'cloud-controller-clock-v1': {
        'summary': "A shared clock",
        'description': '',
        'jobs': [{
            'job_name': 'cloud_controller_clock',
            'mapping': {'db': mapper.jobdb('cc')},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.LTCRelation,
                              contexts.LoggregatorRelation,
                              contexts.MysqlRelation,
                              contexts.CloudControllerRelation,
                              contexts.UAARelation,
                              # diego is coming
                              ]
            }],

    },

    'cloud-controller-v1': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [{
            'job_name': 'cloud_controller_ng',
            'mapping': {'db': mapper.jobdb('cc')},
            'provided_data': [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.MysqlRelation,
                              contexts.LTCRelation,
                              contexts.UAARelation,
                              contexts.CloudControllerRelation.remote_view,

                              # diego is coming
                              # contexts.BundleConfig,
                              # All job context keys
                              # get processed by a name mapper
                              ],
        }]
    },

    'cloud-controller-worker-v1': {
        'summary': "Worker for cc",
        'description': '',
        'jobs': [
            {'job_name': 'cloud_controller_worker',
             'mapping': {'db': mapper.jobdb('cc')},
             'provided_data': [],
             'required_data': [contexts.NatsRelation,
                               contexts.MysqlRelation,
                               contexts.LTCRelation,
                               contexts.UAARelation,
                               contexts.CloudControllerRelation,
                               # diego is coming
                               # contexts.BundleConfig,
                               ],

             }
            ]
    },

    'dea-v1': {
        'summary': 'DEA runs CF apps in containers',
        'description': '',
        'jobs': [{
            'job_name': 'dea_next',
            'mapping': {},
            'required_data': [
                contexts.NatsRelation,
                contexts.LTCRelation,
            ],
        }]

    },

    'dea-logging-agent-v1': {
        'summary': 'Logging Agent for DEA',
        'description': '',
        'jobs': [{
            'job_name': 'dea_logging_agent',
            'mapping': {},
            'required_data': [contexts.NatsRelation,
                              contexts.LTCRelation]
        }]
    },

    'nats-v1': {
        'service': 'nats',
        'summary': 'NATS message bus for CF',
        'jobs': [{
            'job_name': 'nats',
            'mapping': {},
            'required_data': [contexts.NatsRelation.remote_view],
            'provided_data': [contexts.NatsRelation],
        }],
    },

    'nats-stream-forwarder-v1':  {
        'service': 'nats-stream-forwarder',
        'summary': 'NATS stream forwarder',
        'description': '',
        'jobs': [{
            'job_name': 'nats_stream_forwarder',
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.NatsRelation]
            }]
    },

    'router-v1': {
        'service': 'router',
        'summary': 'CF Router',
        'jobs': [{
            'job_name': 'gorouter',
            'ports': [contexts.RouterRelation.port],
            'mapping': {},
            'provided_data': [contexts.RouterRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.LTCRelation,
                              contexts.LoggregatorRelation,
                              contexts.RouterRelation.remote_view],
        }],

    },

    'uaa-v1': {
        'service': 'uaa',
        'summary': 'CF Oauth2 for identity management service',
        'jobs': [
            {'job_name': 'uaa',
             'ports': [8080],
             'mapping':{'db': mapper.jobdb('uaa')},
             'provided_data': [contexts.UAARelation],
             'required_data': [contexts.MysqlRelation,
                               contexts.NatsRelation]
             }
        ]
    },

    'login-v1': {
        'service': 'login',
        'summary': 'login service',
        'description': '',
        'jobs': [{
            'job_name': 'login',
            'ports': [8080],
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.UAARelation]
            }]
        },

    'loggregator-v1': {
        'service': 'loggregator',
        'summary': 'loggregating',
        'description': 'loggregating',
        'jobs': [{
            'job_name': 'loggregator',
            'mapping': {},
            'provided_data': [contexts.LoggregatorRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.EtcdRelation,
                              contexts.LTCRelation]
            }]
        },

    'loggregator-trafficcontroller-v1': {
        'service': 'loggregator-trafficcontroller',
        'summary': 'loggregator-trafficcontroller',
        'description': '',
        'jobs': [{
            'job_name': 'loggregator_trafficcontroller',
            'mapping': {},
            'provided_data': [contexts.LTCRelation],
            'required_data': [contexts.LoggregatorRelation,
                              contexts.LTCRelation.remote_view,
                              contexts.NatsRelation,
                              contexts.CloudControllerRelation]
            }]
        },

    'hm9000-v1': {
        'service': 'hm9000',
        'summary': 'health monitor',
        'description': '',
        'jobs': [{
            'job_name': 'hm9000',
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.CloudControllerRelation,
                              contexts.EtcdRelation]
            }]
        },

    'haproxy-v1': {
        'service': 'haproxy',
        'summary': 'loadbalance the routers',
        'description': '',
        'jobs': [{
            'job_name': 'haproxy',
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.RouterRelation],
            }]
        }
}
