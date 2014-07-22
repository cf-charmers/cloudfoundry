import os
import subprocess
import urllib
import tarfile
import hashlib
import time
import yaml
import stat
import textwrap
import logging

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import services
from charmhelpers import fetch
from cloudfoundry import TEMPLATES_BASE_DIR
from cloudfoundry import PACKAGES_BASE_DIR
from cloudfoundry import contexts
from cloudfoundry import templating
from cloudfoundry.services import SERVICES
from .path import path


logger = logging.getLogger(__name__)


def install_base_dependencies():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby', 'monit']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    enable_monit_http_interface()
    subprocess.check_call(['gem', 'install', '--no-ri', '--no-rdoc', gem_file])


def enable_monit_http_interface():
    enable_http = path('/etc/monit/conf.d/enable_http')

    if enable_http.exists():
        logger.warn("monit http already enabled")
        return

    enable_http.write_text(textwrap.dedent("""
        set httpd port 2812 and
           use address localhost
           allow localhost
        """))

    monit.svc_force_reload()


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
    for i in range(3):
        try:
            _, resp = urllib.urlretrieve(artifact_url, job_archive)
        except (IOError, urllib.ContentTooShortError) as e:
            if os.path.exists(job_archive):
                os.remove(job_archive)
            if i < 2:
                hookenv.log(
                    'Unable to download artifact: {}; retrying (attempt {} of 3)'.format(str(e), i+1),
                    hookenv.INFO)
                time.sleep(i*10+1)
                continue
            else:
                hookenv.log('Unable to download artifact: {}; (attempt {} of 3)'.format(str(e), i+1), hookenv.ERROR)
                raise
        else:
            break

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
        if os.path.exists(job_archive):
            os.remove(job_archive)
        raise


def install_job_packages(job_name):
    package_path = path(get_job_path(job_name)) / 'packages'
    for package in package_path.files('*.tgz'):
        pkgname = package.basename().rsplit('-', 1)[0]
        pkgpath = PACKAGES_BASE_DIR / pkgname
        if not pkgpath.exists():
            pkgpath.mkdir()
            with tarfile.open(package) as tgz:
                tgz.extractall(pkgpath)


def set_script_permissions(job_name):
    jobbin = TEMPLATES_BASE_DIR / job_name / 'bin'
    for script in jobbin.files():
        curr_mode = script.stat().st_mode
        script.chmod(curr_mode | stat.S_IEXEC)


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
    def __init__(self, mapping):
        self.mapping = mapping

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
                src, versioned_dst, self.mapping, spec,
                templates_dir=templates_dir))
        versioned_monit_dst = os.path.join(versioned_dst_dir, 'monit', job_name+'.cfg')
        callbacks.append(templating.RubyTemplateCallback(
            'monit', versioned_monit_dst, self.mapping, spec,
            templates_dir=versioned_src_dir))
        for callback in callbacks:
            if isinstance(callback, services.ManagerCallback):
                callback(manager, job_name, event_name)
            else:
                callback(job_name)
        if os.path.exists(dst_dir):
            os.unlink(dst_dir)
        os.symlink(versioned_dst_dir, dst_dir)
        monit_dst = '/etc/monit/conf.d/{}'.format(job_name)
        if os.path.exists(monit_dst):
            os.unlink(monit_dst)
        os.symlink(versioned_monit_dst, monit_dst)


job_templates = JobTemplates


class Monit(object):
    svc_cmd = ['service', 'monit'] 
    def __init__(self):
        self.name = 'monit'

    def proc(self, cmd, raise_on_err=False):
        try:
            subprocess.check_call(cmd, subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.error('%s: %s', ' '.join(cmd), e.output)
            if raise_on_err:
                raise

    def svc_restart(self, *args):
        cmd = self.svc_cmd + ['start']
        self.proc(cmd, raise_on_err=True)

    def svc_force_reload(self, *args):
        cmd = self.svc_cmd + ['force-reload']
        self.proc(cmd, raise_on_err=True)

    def start(self, jobname):
        cmd = ['monit', 'start', jobname]
        self.proc(cmd, raise_on_err=True)

    def stop(self, jobname):
        cmd = ['monit', 'stop', jobname]
        self.proc(cmd)


monit = Monit()


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
                job_templates(job.get('mapping', {})),
                set_script_permissions,
                monit.svc_force_reload
            ],
            'start': monit.start,
            'stop': monit.stop
        }
        result.append(job_def)
    return result


def db_migrate():
    pass
