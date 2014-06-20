import contexts

__all__ = ['SERVICES']

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
            "provided_data": [contexts.CloudControllerRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.RouterRelation,
                              contexts.MysqlRelation,
                              # contexts.BundleConfig,
                              # All job context keys
                              # get processed by a name mapper
                              ],
        }]
    },

    'nats_v1': {
        'service': 'nats',
        'summary': 'NATS message bus for CF',
        'jobs': [{
            'job_name': 'nats',
            'mapping': {
                'nats.(\w+)': r'properties.nats.\1'
            },
            'provided_data': [contexts.NatsRelation],
        }],
    },

    'router_v1': {
        'service': 'router',
        'summary': 'CF Router',
        'jobs': [{
            'job_name': 'gorouter',
            'ports': [80],
            'mapping': {
                'router.(\w+)': r'properties.router.\1'
            },
            'provided_data': [contexts.RouterRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.LogRouterRelation],
        }],

    },
}
