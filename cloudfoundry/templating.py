import os
import json
import subprocess

from charmhelpers.core import host
from charmhelpers.core import hookenv


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
