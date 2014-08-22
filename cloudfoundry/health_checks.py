from cloudfoundry import tasks


def monit_summary(service):
    result = {
        'name': 'monit_summary',
        'health': 'pass',
        'message': None,
        'data': {},
    }
    summary = tasks.monit.summary()
    if summary is None:
        return dict(result, health='fail', message='unable to get summary')
    if any(v != 'Running' for v in summary.values):
        return dict(result,
                    health='fail',
                    message='not all services running',
                    data={'services': summary})
    return result
