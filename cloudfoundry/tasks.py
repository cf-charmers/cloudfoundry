import os
import subprocess
import tarfile
#import hashlib
import yaml
import stat
import textwrap
import logging
from functools import partial
from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import services
from charmhelpers import fetch
from cloudfoundry import contexts
from cloudfoundry import templating
from cloudfoundry.services import SERVICES
from .path import path

logger = logging.getLogger(__name__)

TEMPLATES_BASE_DIR = path('/var/vcap/jobs')
PACKAGES_BASE_DIR = path('/var/vcap/packages')
RELEASES_DIR = path('/var/vcap/releases')


def install_base_dependencies():
    fetch.apt_install(packages=fetch.filter_installed_packages(['ruby', 'monit', 'runit']))
    gem_file = os.path.join(hookenv.charm_dir(),
                            'files/bosh-template-1.2611.0.pre.gem')
    host.adduser('vcap')
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
    retry = True
    while retry:
        hookenv.log('Downloading {}.tgz from {}'.format(job_name, artifact_url))
        try:
            subprocess.check_call(['wget', '-t0', '-c', '-nv', artifact_url, '-O', job_archive])
        except subprocess.CalledProcessError as e:
            if e.returncode == 4:  # always retry network errors
                hookenv.log('Network error, retrying download', hookenv.WARNING)
                retry = True
            else:
                raise
        else:
            retry = False

    try:
        #assert 'ETag' in resp, (
        #    'Error downloading artifacts from {}; '
        #    'missing ETag (md5) checksum (invalid job?)'.format(artifact_url))
        #expected_md5 = resp['ETag'].strip('"')
        #with open(job_archive) as fp:
        #    actual_md5 = hashlib.md5(fp.read()).hexdigest()
        #assert actual_md5 == expected_md5, (
        #    'Error downloading artifacts from {}; '
        #    'ETag (md5) checksum mismatch'.format(artifact_url))
        with tarfile.open(job_archive) as tgz:
            tgz.extractall(job_path)
    except Exception as e:
        hookenv.log(str(e), hookenv.ERROR)
        if os.path.exists(job_archive):
            os.remove(job_archive)
        raise


def install_job_packages(pkg_base_dir, releases_dir, job_name):
    package_path = path(get_job_path(job_name)) / 'packages'
    version = release_version()
    if not pkg_base_dir.exists():
        pkg_base_dir.makedirs_p(mode=755)

    for package in package_path.files('*.tgz'):
        pkgname = package.basename().rsplit('-', 1)[0]
        pkgpath = releases_dir / version / 'packages' / pkgname
        if not pkgpath.exists():
            pkgpath.makedirs(mode=755)
            with pkgpath:
                subprocess.check_call(['tar', '-xzf', package])

        pkgdest = pkg_base_dir / pkgname
        if not pkgdest.exists():
            pkgpath.symlink(pkgdest)


def set_script_permissions(job_name, tmplt_base_dir=TEMPLATES_BASE_DIR):
    jobbin = tmplt_base_dir / job_name / 'bin'
    for script in jobbin.files():
        curr_mode = script.stat().st_mode
        script.chmod(curr_mode | stat.S_IEXEC)


@hookenv.cached
def get_job_path(job_name):
    version = release_version()
    return path(hookenv.charm_dir()) / 'jobs' / version / job_name


@hookenv.cached
def load_spec(job_name):
    """
    Reads and parses the spec file for the given job name from the jobs folder.
    """
    job_path = get_job_path(job_name)
    with open(os.path.join(job_path, 'spec')) as fp:
        return yaml.safe_load(fp)


@hookenv.cached
def release_version(contexts=contexts):
    units = contexts.OrchestratorRelation()['orchestrator']
    unit = units[0]
    return unit['cf_version']


class JobTemplates(services.ManagerCallback):
    template_base_dir = TEMPLATES_BASE_DIR

    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, manager, job_name, event_name):
        """
        Uses the job spec to render the job's templates.
        """
        version = contexts.\
            OrchestratorRelation()['orchestrator'][0]['cf_version']
        charmdir = path(hookenv.charm_dir())
        versioned_src_dir = charmdir / 'jobs' / version / job_name
        dst_dir = self.template_base_dir / job_name
        versioned_dst_dir = self.template_base_dir / version / job_name
        templates_dir = versioned_src_dir / 'templates'
        spec = load_spec(job_name)
        callbacks = []

        for src, dst in spec.get('templates', {}).iteritems():
            versioned_dst = versioned_dst_dir / dst
            callbacks.append(templating.RubyTemplateCallback(
                src, versioned_dst, self.mapping, spec,
                templates_dir=templates_dir))

        versioned_monit_dst = versioned_dst_dir / ('monit/%s.cfg' % job_name)
        callbacks.append(templating.RubyTemplateCallback(
            'monit', versioned_monit_dst, self.mapping, spec,
            templates_dir=versioned_src_dir))

        for callback in callbacks:
            if isinstance(callback, services.ManagerCallback):
                callback(manager, job_name, event_name)
            else:
                callback(job_name)

        if dst_dir.exists():
            dst_dir.unlink()

        os.symlink(versioned_dst_dir, dst_dir)
        monit_dst = path('/etc/monit/conf.d/{}'.format(job_name))

        if monit_dst.exists():
            monit_dst.unlink()

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
        cmd = ['monit', 'restart', 'all']
        self.proc(cmd, raise_on_err=True)

    def stop(self, jobname):
        cmd = ['monit', 'stop', 'all']
        self.proc(cmd)


monit = Monit()


def build_service_block(charm_name, service_defs=SERVICES):
    service_def = service_defs[charm_name]
    result = []
    for job in service_def.get('jobs', []):
        job_def = {
            'service': job['job_name'],
            'ports': job.get('ports', []),
            'required_data': [contexts.OrchestratorRelation()] +
                             [r() for r in job.get('required_data', [])],
            'provided_data': [p() for p in job.get('provided_data', [])],
            'data_ready': [
                fetch_job_artifacts,
                partial(install_job_packages, PACKAGES_BASE_DIR, RELEASES_DIR),
                job_templates(job.get('mapping', {})),
                set_script_permissions,
            ] + job.get('data_ready', []),
            'start': [monit.start, services.open_ports],
            'stop': [monit.stop, services.close_ports]
        }
        result.append(job_def)
    return result
