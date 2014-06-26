import os
import subprocess
import urllib
import tarfile
import shutil
import yaml

from charmhelpers.core import hookenv
from charmhelpers import fetch
from cloudfoundry import TEMPLATES_BASE_DIR
from cloudfoundry import PACKAGES_BASE_DIR
from cloudfoundry import contexts
from cloudfoundry import services
from cloudfoundry import templating


def install_bosh_template_renderer():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def fetch_job_artifacts(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    job_path = get_job_path(job_name)
    if os.path.exists(job_path):
        return
    artifact_url = os.path.join(
        orchestrator_data['artifacts_url'],
        orchestrator_data['cf_version'],
        'amd64',  # TODO: Get this from somewhere...
        job_name)
    job_archive = job_path+'/'+job_name+'.tgz'
    urllib.urlretrieve(artifact_url, job_archive)
    with tarfile.open(job_archive) as tgz:
        tgz.extractall(job_path)


def install_job_packages(job_name):
    package_path = os.path.join(get_job_path(job_name), 'packages')
    version = contexts.OrchestratorRelation()['cf_version']
    dst_path = os.path.join(PACKAGES_BASE_DIR, job_name)
    versioned_path = os.path.join(PACKAGES_BASE_DIR, version, job_name)
    if os.path.exists(versioned_path):
        return
    shutil.copytree(package_path, versioned_path)
    os.unlink(dst_path)
    os.symlink(versioned_path, dst_path)


@hookenv.cached
def get_job_path(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    return os.path.join(hookenv.charm_dir(), 'jobs', orchestrator_data['cf_version'], job_name)


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
    Uses the job spec to generate the list of callbacks to render the job's
    templates.
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


def build_service_block(charm_name, services=services.SERVICES):
    service_def = services[charm_name]
    result = []
    for job in service_def.get('jobs', []):
        job_def = {
            'service': job['job_name'],
            'required_data': [r() for r in
                              [contexts.OrchestratorRelation] +
                              job.get('required_data', [])],
            'provided_data': [p() for p in job.get('provided_data', [])],
            'data_ready': [
                fetch_job_artifacts,
                install_job_packages,
            ] + job_templates(job['job_name']),
        }
        result.append(job_def)
    return result


def db_migrate():
    pass
