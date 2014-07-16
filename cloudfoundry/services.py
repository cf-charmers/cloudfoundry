import contexts

__all__ = ['SERVICES']

SERVICES = {
    'cloud-controller-clock-v1': {
        'summary': "A shared clock",
        'description': '',
        'jobs': [{
            'job_name': 'cloud_controller_clock',
            'mapping': {
                'nats.(\w+)': r'properties.nats.\1',  # TODO: use callback for list
                'db.(\w+)': r'properties.ccdb.\1',
                'uaa.(\w+)': r'properties.uaa.\1',
                'cc.(\w+)': r'properties.cc.\1',
                'login.(\w+)': r'properties.login.\1',
                'syslog_aggregator.(\w+)': r'properties.syslog_aggregator.\1',
                # TODO see: logger_endpoint.. may need to extend loggregator context
                'loggregator_endpoint.(\w+)': r'properties.loggregator_endpoint.\1'
                },
            'provided_data': [contexts.ClockRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.LoggregatorRelation,
                              contexts.MysqlRelation,
                              contexts.CloudControllerRelation,
                              contexts.LoginRelation,
                              contexts.UAARelation,
                              contexts.SyslogAggregatorRelation
                              # diego is coming
                              ]
            }],

    },

    'cloud-controller-v1': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [{
            'job_name': 'cf_cloudcontroller_ng',
            'mapping': {
                'cc.(\w+)': r'properties.cc.\1',
                'nats.(\w+)': r'properties.nats.\1',  # TODO: use callback for list
                'uaa.(\w+)': r'properties.uaa.\1',
                'db.(\w+)': r'properties.ccdb.\1',
                'dea.(\w+)': r'properties.dea_next.\1',
                'login.(\w+)': r'properties.login.\1',
                'syslog_aggregator.(\w+)': r'properties.syslog_aggregator.\1',
                #TODO see: logger_endpoint.. may need to extend loggregator context
                'loggregator_endpoint.(\w+)': r'properties.loggregator_endpoint.\1'
            },
            'provided_data': [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.MysqlRelation,
                              contexts.LoggregatorRelation,
                              contexts.ClockRelation,
                              contexts.UAARelation,
                              contexts.DEARelation,
                              contexts.LoginRelation,
                              contexts.SyslogAggregatorRelation
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
             'mapping': {
                 'nats.(\w+)': r'properties.nats.\1',  # TODO: use callback for list
                 'uaa.(\w+)': r'properties.uaa.\1',
                 'db.(\w+)': r'properties.ccdb.\1',
                 'dea.(\w+)': r'properties.dea_next.\1',
                 'login.(\w+)': r'properties.login.\1',
                 'syslog_aggregator.(\w+)': r'properties.syslog_aggregator.\1',
                 #TODO see: logger_endpoint.. may need to extend loggregator context
                 'loggregator_endpoint.(\w+)': r'properties.loggregator_endpoint.\1'
             },
             'provided_data': [],
             'required_data': [contexts.NatsRelation,
                               contexts.MysqlRelation,
                               contexts.LoggregatorRelation,
                               contexts.UAARelation,
                               contexts.DEARelation,
                               contexts.LoginRelation,
                               contexts.SyslogAggregatorRelation
                               # diego is coming
                               # contexts.BundleConfig,
                               # All job context keys
                               # get processed by a name mapper
                               ],
             }
            ]

    },

    'dea-v1': {
        'summary': 'DEA runs CF apps in containers',
        'description': '',
        'jobs': [{
            'job_name': 'dea_next',
            'mapping': {
                'dea.(\w+)': r'properties.dea_next.\1',
            },
            'required_data': [
                contexts.NatsRelation,
                contexts.LogRouterRelation,
            ],
        }]

    },

    'dea-logging-agent-v1': {
        'summary': 'Logging Agent for DEA',
        'description': '',
        'jobs': [{
            'job_name': 'dea_logging_agent',
            'mapping': {'dea_logging_agent.(\w+)': r'properties.\1'},
            'required_data': [
                contexts.NatsRelation,
            ]
        }]
    },

    'nats-v1': {
        'service': 'nats',
        'summary': 'NATS message bus for CF',
        'jobs': [{
            'job_name': 'nats',
            'mapping': {'nats.(\w+)': r'properties.nats.\1'},
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
            'mapping': {
                'syslog_aggregator.(\w+)': r'properties.syslog_aggregator.\1',
                'nats.(\w+)': r'properties.nats.\1'  # needs callable
                },
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.SyslogAggregatorRelation]
            }]
    },

    'router-v1': {
        'service': 'router',
        'summary': 'CF Router',
        'jobs': [{
            'job_name': 'gorouter',
            'ports': [80],
            'mapping': {
                'router.(\w+)': r'properties.router.\1',
            },
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.LogRouterRelation,
                              contexts.LoggregatorRelation,
                              contexts.SyslogAggregatorRelation],
        }],

    },

    'uaa-v1': {
        'service': 'uaa',
        'summary': 'CF Oauth2 for identity management service',
        'jobs': [
            {'job_name': 'uaa',
             'ports': [8080],
             'mapping':{
                 'uaa.(\w+)': r'properties.uaa.\1',
                 'db.(\w+)': r'properties.uaa.db.\1'
                 },
             'provided_data': [],
             'required_data':[contexts.MysqlRelation]
             }
        ]
    },

    'login-v1': {
        'service': 'login',
        'summary': 'login',
        'description': '',
        'jobs': [{
            'job_name': 'login',
            'ports': [8080],
            'mapping': {
                'uaa.(\w+)', r'properties.uaa.\1',
                'syslog_aggregator.(\w+)', r'properties.syslog_aggregator.\1',
                'nats.(\w+)', r'properties.nats.\1',  # needs callable
            },
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.UAARelation,
                              contexts.SyslogAggregatorRelation
                              ]
            }]
        },

    'loggregator-v1': {
        'service': 'loggregator',
        'summary': 'loggregating',
        'description': 'loggregating',
        'jobs': [{
            'job_name': 'loggregator',
            'mapping': {'nats.(\w+)', r'properties.nats.\1',  # needs callable
                        'syslog_aggregator.(\w+)', r'properties.syslog_aggregator.\1'
                        },
            'provided_data': [contexts.LoggregatorRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.SyslogAggregatorRelation
                              ]
            }]
        },

    'loggregator-trafficcontroller-v1': {
        'service': 'loggregator-trafficcontroller',
        'summary': 'loggregator-trafficcontroller',
        'description': '',
        'jobs': [{
            'job_name': 'loggregator_trafficcontroller',
            'mapping': {'loggregator.(\w+)', r'properties.loggregator.\1',  # needs callable
                        'syslog_aggregator.(\w+)', r'properties.syslog_aggregator.\1',
                        'nats.(\w+)', r'properties.nats.\1',  # needs callable
                        },
            'provided_data': [],
            'required_data': [contexts.LoggregatorRelation,
                              contexts.NatsRelation,
                              contexts.SyslogAggregatorRelation,
                              ]
            }]
        },

    'hm9000-v1': {
        'service': 'hm9000',
        'summary': 'health monitor',
        'description': '',
        'jobs': [{
            'job_name': 'hm9000',
            'mapping': {'syslog_aggregator.(\w+)', r'properties.syslog_aggregator.\1',
                        'cc.(\w+)', r'properties.cc.\1',
                        'etcd.(\w+)', r'properties.etcd.\1',
                        'nats.(\w+)', r'properties.nats.\1'},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.CloudControllerRelation,
                              contexts.EtcdRelation,
                              contexts.SyslogAggregatorRelation]
            }]
        },

    'syslog-aggregator-v1': {
        'service': 'syslog-aggregator',
        'summary': 'aggregates the syslogs',
        'description': '',
        'jobs': [{
            'job_name': 'syslog_aggregator',
            'mapping': {},
            'provided_data': [contexts.SyslogAggregatorRelation],
            'required_data': []
            }]
        },

    'haproxy-v1': {
        'service': 'haproxy',
        'summary': 'loadbalance the routers',
        'description': '',
        'jobs': [{
            'job_name': 'haproxy',
            'mapping': {'syslog_aggregator.(\w+)', r'properties.syslog_aggregator.\1',
                        'router.(\w+)', r'properties.router.\1'},
            'provided_data': [],
            'required_data':[contexts.SyslogAggregatorRelation]
            }]
        }
}
