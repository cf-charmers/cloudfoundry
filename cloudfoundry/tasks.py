import os
import subprocess
import urllib
import tarfile
import shutil
import hashlib
import yaml

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import services
from charmhelpers import fetch
from cloudfoundry import TEMPLATES_BASE_DIR
from cloudfoundry import PACKAGES_BASE_DIR
from cloudfoundry import contexts
from cloudfoundry import templating
from cloudfoundry.services import SERVICES


def install_bosh_template_renderer():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    subprocess.check_call(['gem', 'install', gem_file])


def fetch_job_artifacts(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    job_path = get_job_path(job_name)
    job_archive = job_path+'/'+job_name+'.tgz'
    artifact_url = os.path.join(
        orchestrator_data['orchestrator'][0]['artifacts_url'],
        'cf-'+orchestrator_data['orchestrator'][0]['cf_version'],
        'amd64',  # TODO: Get this from somewhere...
        job_name)
    if os.path.exists(job_archive):
        return
    host.mkdir(job_path)
    _, resp = urllib.urlretrieve(artifact_url, job_archive)
    try:
        assert 'ETag' in resp, (
            'Error downloading artifacts from {}; '
            'missing ETag (md5) checksum (invalid job?)'.format(artifact_url))
        expected_md5 = resp['ETag'].strip('"')
        with open(job_archive) as fp:
            actual_md5 = hashlib.md5(fp.read()).hexdigest()
        assert actual_md5 == expected_md5, (
            'Error downloading artifacts from {}; '
            'ETag (md5) checksum mismatch'.format(artifact_url))
        with tarfile.open(job_archive) as tgz:
            tgz.extractall(job_path)
    except Exception as e:
        hookenv.log(str(e), hookenv.ERROR)
        os.remove(job_archive)
        raise


def install_job_packages(job_name):
    package_path = os.path.join(get_job_path(job_name), 'packages')
    version = contexts.OrchestratorRelation()['orchestrator'][0]['cf_version']
    dst_path = os.path.join(PACKAGES_BASE_DIR, job_name)
    versioned_path = os.path.join(PACKAGES_BASE_DIR, version, job_name)
    if os.path.exists(versioned_path):
        return
    shutil.copytree(package_path, versioned_path)
    if os.path.exists(dst_path):
        os.unlink(dst_path)
    os.symlink(versioned_path, dst_path)


@hookenv.cached
def get_job_path(job_name):
    orchestrator_data = contexts.OrchestratorRelation()
    version = orchestrator_data['orchestrator'][0]['cf_version']
    return os.path.join(hookenv.charm_dir(), 'jobs', version, job_name)


@hookenv.cached
def load_spec(job_name):
    """
    Reads and parses the spec file for the given job name from the jobs folder.
    """
    job_path = get_job_path(job_name)
    with open(os.path.join(job_path, 'spec')) as fp:
        return yaml.safe_load(fp)


class JobTemplates(services.ManagerCallback):
    def __call__(self, manager, job_name, event_name):
        """
        Uses the job spec to render the job's templates.
        """
        version = contexts.OrchestratorRelation()['orchestrator'][0]['cf_version']
        versioned_src_dir = os.path.join(hookenv.charm_dir(), 'jobs', version, job_name)
        dst_dir = os.path.join(TEMPLATES_BASE_DIR, job_name)
        versioned_dst_dir = os.path.join(TEMPLATES_BASE_DIR, version, job_name)
        templates_dir = os.path.join(versioned_src_dir, 'templates')
        spec = load_spec(job_name)
        callbacks = []
        for src, dst in spec.get('templates', {}).iteritems():
            versioned_dst = os.path.join(versioned_dst_dir, dst)
            callbacks.append(templating.RubyTemplateCallback(
                src, versioned_dst,
                templates_dir=templates_dir))
        versioned_monit_dst = os.path.join(versioned_dst_dir, 'monit', job_name+'.cfg')
        callbacks.append(templating.RubyTemplateCallback(
            'monit', versioned_monit_dst,
            templates_dir=versioned_src_dir))
        for callback in callbacks:
            if isinstance(callback, services.ManagerCallback):
                callback(manager, job_name, event_name)
            else:
                callback(job_name)
        if os.path.exists(dst_dir):
            os.unlink(dst_dir)
        os.symlink(versioned_dst_dir, dst_dir)
        monit_dst = '/etc/monit.d/{}.cfg'.format(job_name)
        if os.path.exists(monit_dst):
            os.unlink(monit_dst)
        os.symlink(versioned_monit_dst, monit_dst)
job_templates = JobTemplates()


def build_service_block(charm_name, services=SERVICES):
    service_def = services[charm_name]
    result = []
    for job in service_def.get('jobs', []):
        job_def = {
            'service': job['job_name'],
            'required_data': [contexts.OrchestratorRelation()] +
                             [r() for r in job.get('required_data', [])],
            'provided_data': [p() for p in job.get('provided_data', [])],
            'data_ready': [
                fetch_job_artifacts,
                install_job_packages,
                job_templates,
            ],
        }
        result.append(job_def)
    return result


def db_migrate():
    pass
