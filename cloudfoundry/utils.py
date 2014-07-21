import os
import subprocess

from tornado.options import define, options
from jujuclient import Environment


def current_env():
    return subprocess.check_output(['juju', 'switch']).strip()


def get_env(name=None, user="user-admin", password=None):
    # A hook env will have this set
    api_addresses = os.environ.get('JUJU_API_ADDRESSES')
    if not api_addresses:
        # use the local option/connect which
        # parses local jenv info
        env = Environment.connect(name or options.env_name)
    else:
        env = Environment(api_addresses.split()[0])
        env.login(user=user,
                  password=password or options.password)
    return env


def record_pid():
    pid_dir = os.path.expanduser('~/.config/juju-deployer')
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    with open(os.path.join(pid_dir, 'server.pid'), 'w') as fp:
        fp.write('%s\n' % os.getpid())


define("env_name", default=current_env(), help="env to manage", type=str)
