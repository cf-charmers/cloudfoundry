import contexts
import mapper
import tasks
import utils

__all__ = ['SERVICES']


SERVICES = {
    'cloud-controller-clock-v1': {
        'summary': "A shared clock",
        'description': '',
        'jobs': [{
            'job_name': 'cloud_controller_clock',
            'mapping': {'cc-db': mapper.ccdb},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.LTCRelation,
                              contexts.LoggregatorRelation,
                              contexts.CloudControllerRelation,
                              contexts.UAARelation,
                              contexts.CloudControllerDBRelation,
                              ]
            }],

    },

    'cloud-controller-clock-v2': {
        'summary': "A shared clock",
        'description': '',
        'jobs': [
            {'job_name': 'cloud_controller_clock',
             'mapping': {'cc-db': mapper.ccdb},
             'provided_data': [],
             'required_data': [contexts.NatsRelation,
                               contexts.LTCRelation,
                               contexts.LoggregatorRelation,
                               contexts.CloudControllerRelation,
                               contexts.UAARelation,
                               contexts.CloudControllerDBRelation,
                               ]},
            {'job_name': 'metron_agent',
             'required_data': [contexts.LTCRelation,
                               contexts.NatsRelation,
                               contexts.LoggregatorRelation,
                               contexts.EtcdRelation]},
            ],

    },

    'cloud-controller-v1': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [{
            'job_name': 'cloud_controller_ng',
            'mapping': {'db': mapper.ccdb},
            'provided_data': [contexts.CloudControllerRelation,
                              contexts.CloudControllerDBRelation],
            'required_data': [contexts.NatsRelation,
                              contexts.MysqlRelation,
                              contexts.LTCRelation,
                              contexts.UAARelation,
                              contexts.CloudControllerRelation.remote_view,
                              ],
            'data_ready': [
                contexts.CloudControllerDBRelation.send_data,
            ],
        }]
    },

    'cloud-controller-v2': {
        'summary': 'CF Cloud Controller, the brains of the operation',
        'description': '',
        'jobs': [
            {'job_name': 'cloud_controller_ng',
             'mapping': {'db': mapper.ccdb},
             'provided_data': [contexts.CloudControllerRelation,
                               contexts.CloudControllerDBRelation],
             'required_data': [contexts.NatsRelation,
                               contexts.MysqlRelation,
                               contexts.LTCRelation,
                               contexts.UAARelation,
                               contexts.CloudControllerRelation.remote_view,
                               ],
             'data_ready': [
                 contexts.CloudControllerDBRelation.send_data,
             ]},
            {'job_name': 'metron_agent',
             'required_data': [contexts.LTCRelation,
                               contexts.NatsRelation,
                               contexts.LoggregatorRelation,
                               contexts.EtcdRelation]},
        ]
    },

    'cloud-controller-worker-v1': {
        'summary': "Worker for cc",
        'description': '',
        'jobs': [
            {'job_name': 'cloud_controller_worker',
             'mapping': {'cc-db': mapper.ccdb},
             'provided_data': [],
             'required_data': [contexts.NatsRelation,
                               contexts.LTCRelation,
                               contexts.UAARelation,
                               contexts.CloudControllerRelation,
                               contexts.CloudControllerDBRelation,
                               ],

             }
            ]
    },

    'cloud-controller-worker-v2': {
        'summary': "Worker for cc",
        'description': '',
        'jobs': [
            {'job_name': 'cloud_controller_worker',
             'mapping': {'cc-db': mapper.ccdb},
             'provided_data': [],
             'required_data': [contexts.NatsRelation,
                               contexts.LTCRelation,
                               contexts.UAARelation,
                               contexts.CloudControllerRelation,
                               contexts.CloudControllerDBRelation,
                               ],

             },
            {'job_name': 'metron_agent',
             'required_data': [contexts.LTCRelation,
                               contexts.NatsRelation,
                               contexts.LoggregatorRelation,
                               contexts.EtcdRelation]},
            ]
    },

    'dea-v1': {
        'summary': 'DEA runs CF apps in containers',
        'description': '',
        'jobs': [
            {
                'job_name': 'dea_next',
                'mapping': {},
                'install': [
                    utils.install_linux_image_extra,
                    utils.apt_install(['quota']),
                    utils.modprobe(['quota_v1', 'quota_v2'])
                ],
                'required_data': [
                    contexts.NatsRelation,
                    contexts.LTCRelation,
                    contexts.DEARelation.remote_view,
                ],
                'data_ready': [
                    # Apply our workaround till we
                    # have a real fix
                    tasks.patch_dea
                ]
            },
            {
                'job_name': 'dea_logging_agent',
                'mapping': {},
                'required_data': [contexts.NatsRelation,
                                  contexts.LTCRelation]
            },
        ]

    },

    'dea-v2': {
        'summary': 'DEA runs CF apps in containers',
        'description': '',
        'jobs': [
            {
                'job_name': 'dea_next',
                'mapping': {},
                'install': [
                    utils.install_linux_image_extra,
                    utils.apt_install(['quota']),
                    utils.modprobe(['quota_v1', 'quota_v2'])
                ],
                'required_data': [
                    contexts.NatsRelation,
                    contexts.LTCRelation,
                    contexts.DEARelation.remote_view,
                ],
                'data_ready': [
                    # Apply our workaround till we
                    # have a real fix
                    tasks.patch_dea
                ]
            },
            {
                'job_name': 'dea_logging_agent',
                'mapping': {},
                'required_data': [contexts.NatsRelation,
                                  contexts.LTCRelation]
            },
            {'job_name': 'metron_agent',
             'required_data': [contexts.LTCRelation,
                               contexts.NatsRelation,
                               contexts.LoggregatorRelation,
                               contexts.EtcdRelation]},
        ]

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

    'router-v2': {
        'service': 'router',
        'summary': 'CF Router',
        'jobs': [
            {'job_name': 'gorouter',
             'ports': [contexts.RouterRelation.port],
             'mapping': {},
             'provided_data': [contexts.RouterRelation],
             'required_data': [contexts.NatsRelation,
                               contexts.LTCRelation,
                               contexts.LoggregatorRelation,
                               contexts.RouterRelation.remote_view]},
            {'job_name': 'metron_agent',
             'required_data': [contexts.LTCRelation,
                               contexts.NatsRelation,
                               contexts.LoggregatorRelation,
                               contexts.EtcdRelation]},
        ],

    },

    'uaa-v1': {
        'service': 'uaa',
        'summary': 'CF Oauth2 for identity management service',
        'jobs': [
            {'job_name': 'uaa',
             'mapping': {'db': mapper.uaadb},
             'provided_data': [contexts.UAARelation],
             'required_data': [contexts.MysqlRelation,
                               contexts.NatsRelation,
                               contexts.UAARelation.remote_view]
             }
        ]
    },

    'login-v1': {
        'service': 'login',
        'summary': 'login service',
        'description': '',
        'jobs': [{
            'job_name': 'login',
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.NatsRelation,
                              contexts.UAARelation,
                              contexts.LoginRelation.remote_view]
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
                              contexts.LTCRelation,
                              contexts.LoggregatorRelation.remote_view]
            }]
        },

    'loggregator-trafficcontroller-v1': {
        'service': 'loggregator-trafficcontroller',
        'summary': 'loggregator-trafficcontroller',
        'description': '',
        'jobs': [{
            'job_name': 'loggregator_trafficcontroller',
            'ports': [contexts.LTCRelation.outgoing_port],
            'mapping': {},
            'provided_data': [contexts.LTCRelation],
            'required_data': [contexts.LoggregatorRelation,
                              contexts.LTCRelation.remote_view,
                              contexts.NatsRelation,
                              contexts.CloudControllerRelation,
                              contexts.EtcdRelation]
            }]
        },

    'loggregator-trafficcontroller-v2': {
        'service': 'loggregator-trafficcontroller',
        'summary': 'loggregator-trafficcontroller',
        'description': '',
        'jobs': [
            {'job_name': 'loggregator_trafficcontroller',
             'ports': [contexts.LTCRelation.outgoing_port],
             'mapping': {},
             'provided_data': [contexts.LTCRelation],
             'required_data': [contexts.LoggregatorRelation,
                               contexts.LTCRelation.remote_view,
                               contexts.NatsRelation,
                               contexts.CloudControllerRelation,
                               contexts.EtcdRelation]},
            ]
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
            'ports': [contexts.RouterRelation.port],
            'mapping': {},
            'provided_data': [],
            'required_data': [contexts.RouterRelation],
            }]
        }
}
