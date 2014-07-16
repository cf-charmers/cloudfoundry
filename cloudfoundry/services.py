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
            'provided_data': [],  # TODO: context.ClockRelation
            'required_data':[contexts.NatsRelation,
                             contexts.LoggregatorRelation,
                             contexts.MysqlRelation,
                             contexts.CloudControllerRelation,
                             #TODO: context.LoginRelation
                             #TODO: context.UAARelation,
                             #TODO: context.SyslogAggregatorRelation
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
                              #TODO: context.ClockRelation,
                              #TODO: context.UAARelation,
                              #TODO: context.DEARelation
                              #TODO: context.LoginRelation
                              #TODO: context.SyslogAggregatorRelation
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
                               #TODO: context.UAARelation,
                               #TODO: context.DEARelation
                               #TODO: context.LoginRelation
                               #TODO: context.SyslogAggregatorRelation
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

    'nats-stream-forwarder-v1': {},

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
                              contexts.LogRouterRelation],
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

    'login-v1': {},

    'loggregator-v1': {},

    'loggregator-trafficcontroller-v1': {},

    'hm9000-v1': {},

    'syslog-aggregator-v1': {},

    'haproxy-v1': {}
}
