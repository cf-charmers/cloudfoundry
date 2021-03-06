import logging
from utils import NestedDict

logger = logging.getLogger(__name__)


def flatten(data):
    result = {}

    def _f(o, p):
        for k, v in o.items():
            if isinstance(v, dict):
                _f(v, p + [k])
            else:
                key = '.'.join(p + [k])
                result[key] = v
    _f(data, [])
    return result


def property_mapper(mapping, data_source):
    result = NestedDict()
    if getattr(data_source, 'name', None) in mapping:
        result.update(mapping[data_source.name](data_source))
    elif hasattr(data_source, 'erb_mapping'):
        result.update(data_source.erb_mapping())
    else:
        for key, value in data_source.iteritems():
            if key in mapping:
                result.update(mapping[key](value))
            else:
                result[key] = value
    return result


def uaadb(data):
    """
    Remaps uaa's connection to mysql

    #@@ HA may change this case
    """
    db = data['db'][0]

    uaa_db = dict(tag='uaa',
                  name=db['database'])

    creds = dict(tag='admin',
                 name=db['user'],
                 password=db['password'])

    return dict(uaadb=dict(db_scheme='mysql',
                           address=db['host'],
                           port=db['port'],
                           databases=[uaa_db],
                           roles=[creds]))


def ccdb(data):
    """
    Mapper from a MysqlRelation to a ccdb block for use in the templates.

    #@@ This may need to be adjusted to scale / HA the databases.
    """
    db = data.get('db', data.get('cc-db'))[0]

    job_db = dict(tag='cc',
                  name=db['database'])

    creds = dict(tag='admin',
                 name=db['user'],
                 password=db['password'])

    return {
        'ccdb': {
            'db_scheme': 'mysql2',
            'address': db['host'],
            'port': db['port'],
            'databases': [job_db],
            'roles': [creds],
        },
    }
