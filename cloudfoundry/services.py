import contexts
import tasks

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
            'data_ready': [tasks.job_templates, tasks.db_migrate, ],
        }]
    },
    'nats_v1': {},
    'router_v1': {},
}
