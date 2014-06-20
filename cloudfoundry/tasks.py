import os
import subprocess
import yaml
import urllib
import tarfile

from charmhelpers.core import hookenv
from charmhelpers import fetch
from cloudfoundry import TEMPLATES_BASE_DIR
from cloudfoundry import templating
from cloudfoundry import contexts


def install_bosh_template_renderer():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def fetch_job_artifacts(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    artifact_url = '{}/{}/{}.tgz'.format(
        orchestrator_data['artifacts_url'], orchestrator_data['cf_release'], job_name)
    job_path = get_job_path(job_name)
    job_archive = job_path+'/'+job_name+'.tgz'
    urllib.urlretrieve(artifact_url, job_archive)
    with tarfile.open(job_archive) as tgz:
        tgz.extractall(job_path)


def install_service_packages(service_name):
    pass


@hookenv.cached
def get_job_path(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    return os.path.join(hookenv.charm_dir(), 'jobs', orchestrator_data['cf_release'], job_name)


@hookenv.cached
def load_spec(job_name):
    """
    Reads and parses the spec file for the given job name from the jobs folder.
    """
    job_path = get_job_path(job_name)
    with open(os.path.join(job_path, 'spec')) as fp:
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
