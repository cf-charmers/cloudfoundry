import os
import json
import copy
import subprocess

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import services
from cloudfoundry.mapper import NestedDict, property_mapper


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
    content = subprocess.check_output([
        'bosh-template', source, '-C', json.dumps(context)])
    host.mkdir(os.path.dirname(target))
    host.write_file(target, content, owner, group, perms)


def deepmerge(dest, src):
    result = copy.deepcopy(dest)
    for k, v in src.iteritems():
        if k in dest and isinstance(v, dict):
            result[k] = deepmerge(dest[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


class RubyTemplateCallback(services.TemplateCallback):
    """
    Callback class that will render a Ruby template, for use as a ready action.
    """
    def __init__(self, source, target, mapping, spec, owner='root', group='root', perms=0444, templates_dir=None):
        super(RubyTemplateCallback, self).__init__(source, target, owner, group, perms)
        self.templates_dir = templates_dir
        self.mapping = mapping
        self.defaults = NestedDict()
        self.defaults.update({k: v.get('default') for k, v in spec['properties'].iteritems()})
        self.defaults.setdefault('networks', {})['apps'] = 'default'

    def collect_data(self, manager, service_name):
        service = manager.get_service(service_name)
        data = {}
        for data_source in service.get('required_data', []):
            data = deepmerge(data, data_source)
        defaults = {
            'networks': {'default': {'ip': hookenv.unit_get('private-address')}},
            'properties': NestedDict(self.defaults),
        }
        data = property_mapper(self.mapping, data)
        data = deepmerge(defaults, data)
        return data

    def __call__(self, manager, service_name, event_name):
        context = self.collect_data(manager, service_name)
        render_erb(self.source, self.target, context,
                   self.owner, self.group, self.perms,
                   self.templates_dir)
