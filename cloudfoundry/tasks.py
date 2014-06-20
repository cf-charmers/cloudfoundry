import os
import subprocess
import yaml

from charmhelpers.core import hookenv
from charmhelpers import fetch
from cloudfoundry import TEMPLATES_BASE_DIR
from cloudfoundry import templating


def install_bosh_template_renderer():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def install_service_packages(service_name):
    pass


@hookenv.cached
def load_spec(job_name):
    """
    Reads and parses the spec file for the given job name from the jobs folder.
    """
    with open(os.path.join(hookenv.charm_dir(), 'jobs', job_name, 'spec')) as fp:
        return yaml.safe_load(fp)


def job_templates(job_name):
    """
    Uses the job spec to generate the list of callbacks to render the job's templates.
    """
    spec = load_spec(job_name)
    callbacks = []
    for src, dst in spec.get('templates', {}).iteritems():
        callbacks.append(templating.RubyTemplateCallback(
            os.path.join('templates', src),
            os.path.join(TEMPLATES_BASE_DIR, job_name, dst),
            templates_dir=os.path.join(hookenv.charm_dir(), 'jobs')))
    callbacks.append(templating.RubyTemplateCallback(
        'monit', '/etc/monit.d/{}.cfg'.format(job_name),
        templates_dir=os.path.join(hookenv.charm_dir(), 'jobs')))
    return callbacks


def db_migrate():
    pass
