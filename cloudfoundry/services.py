import contexts

__all__ = ['SERVICES']

SERVICES = {
    'cc-clock-v1': {
        'summary': 'Cloud Controller Clock',
        'description': '',
        'jobs': [{
            'job_name': 'cloud-controller-clock',
            'mapping': (),
            "provided_data": [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.MysqlRelation,
                              ],
        }]
    },
    'cloud-controller-v1': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [{
            'job_name': 'cf-cloudcontroller-ng',
            'mapping': (),
            'provided_data': [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.RouterRelation,
                              contexts.MysqlRelation,
                              ],
        }]
    },

    'dea-v1': {
        'summary': 'DEA runs CF apps in containers',
        'description': '',
        'jobs': [{
            'job_name': 'dea_next',
            'mapping': (
                ('dea.(\w+)', r'properties.dea_next.\1'),
            ),
            'required_data': [
                contexts.NatsRelation,
                contexts.LogRouterRelation,
                contexts.RouterRelation
            ],
        }]

    },

    'dea-logging-agent-v1': {
        'summary': 'Logging Agent for DEA',
        'description': '',
        'jobs': [{
            'job_name': 'dea_logging_agent',
            'mapping': (('dea_logging_agent.(\w+)', r'properties'),),
            'required_data': [
                contexts.NatsRelation,
                contexts.RouterRelation
            ]
        }]
    },

    'nats-v1': {
        'service': 'nats',
        'summary': 'NATS message bus for CF',
        'jobs': [{
            'job_name': 'nats',
            'mapping': (('nats.(\w+)', r'properties.nats.\1'),),
            'provided_data': [contexts.NatsRelation],
        }],
    },

    'router-v1': {
        'service': 'router',
        'summary': 'CF Router',
        'jobs': [{
            'job_name': 'gorouter',
            'ports': [80],
            'mapping': [
                ('router.(\w+)', r'properties.router.\1'),
            ],
            'provided_data': [contexts.RouterRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.LogRouterRelation],
        }],

    },
}
