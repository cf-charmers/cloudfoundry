import os
import json
import copy
import subprocess
import logging

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import services
from cloudfoundry.mapper import NestedDict, property_mapper
from cloudfoundry.utils import deepmerge

logger = logging.getLogger(__name__)


def render_erb(source, target, context, owner='root', group='root', perms=0444, templates_dir=None):
    """
    Render a template.

    The `source` path, if not absolute, is relative to the `templates_dir`.

    The `target` path should be absolute.

    The context should be a dict containing the values to be replaced in the
    template.

    The `owner`, `group`, and `perms` options will be passed to `write_file`.

    If omitted, `templates_dir` defaults to the `templates` folder in the charm.

    Note: Using this requires ruby to be installed.
    """
    if templates_dir is None:
        templates_dir = os.path.join(hookenv.charm_dir(), 'templates')
    if not os.path.isabs(source):
        source = os.path.join(templates_dir, source)

    try:
        cmd = ['bosh-template', source, '-C', json.dumps(context)]
        content = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logger.error('Failed template rendering:%s\n%s\n%s',
                     source,
                     json.dumps(context, indent=2),
                     e.output)
        cmd[-1] = '<json>'
        raise RuntimeError("Rendering failed:\n%s" % ' '.join(cmd))

    host.mkdir(os.path.dirname(target))
    host.write_file(target, content, owner, group, perms)


class RubyTemplateCallback(services.TemplateCallback):
    """
    Callback class that will render a Ruby template, for use as a ready action.
    """
    def __init__(self, source, target, mapping, spec, owner='root', group='root', perms=0444, templates_dir=None):
        super(RubyTemplateCallback, self).__init__(source, target, owner, group, perms)
        self.templates_dir = templates_dir
        self.mapping = mapping
        self.defaults = NestedDict()
        self.name = spec['name']
        self.defaults.update({k: v.get('default')
                              for k, v in spec['properties'].iteritems()
                              if isinstance(v, dict)})
        self.defaults.setdefault('networks', {})['apps'] = 'default'

    def collect_data(self, manager, service_name):
        service = manager.get_service(service_name)
        unit_num = int(hookenv.local_unit().split('/')[-1])
        data = {
            'index': unit_num,
            'job': {'name': self.name},
            'networks': {'default': {'ip': hookenv.unit_get('private-address')}},
            'properties': copy.deepcopy(self.defaults),
        }
        for data_source in service.get('required_data', []):
            deepmerge(data['properties'], property_mapper(self.mapping, data_source))
        return data

    def __call__(self, manager, service_name, event_name):
        context = self.collect_data(manager, service_name)
        render_erb(self.source, self.target, context,
                   self.owner, self.group, self.perms,
                   self.templates_dir)
