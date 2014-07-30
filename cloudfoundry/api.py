import os
import shutil
from charmhelpers.core import hookenv

from deployer.env.gui import GUIEnvironment
from deployer.utils import get_qualified_charm_url
from deployer.utils import parse_constraints
from deployer.deployment import Deployment


class JujuLoggingDeployment(Deployment):
    def _handle_feedback(self, feedback):
        for e in feedback.get_errors():
            hookenv.log(e, level=hookenv.ERROR)
        for e in feedback.get_warnings():
            hookenv.log(e, level=hookenv.WARNING)
        assert not feedback.has_errors, '\n'.join(feedback.get_errors())


class APIEnvironment(GUIEnvironment):
    """
    Environment subclass that uses the APi but supports local charms.
    """
    def deploy(self, name, charm_url, repo=None, config=None, constraints=None,
               num_units=1, force_machine=None):
        charm_url = get_qualified_charm_url(charm_url)
        constraints = parse_constraints(constraints)
        if charm_url.startswith('local:'):
            series, charm_id = charm_url.split(':')[1].split('/')
            charm_name = charm_id.rsplit('-', 1)[0]
            charm_file = os.path.join('/tmp', charm_id)
            charm_path = os.path.join(repo, series, charm_name)
            shutil.make_archive(charm_file, 'zip', charm_path)
            archive = charm_file + '.zip'
            size = os.path.getsize(archive)
            with open(archive) as fp:
                self.client.add_local_charm(fp, series, size)
        else:
            self.client.add_charm(charm_url)
        self.client.deploy(
            name, charm_url, config=config, constraints=constraints,
            num_units=num_units, machine_spec=force_machine)

    def _get_units_in_error(self, status=None):
        """
        Ignore this unit when watching for errors, lest we are never
        able to get out of an error state with `resolved --retry`.
        """
        units = super(APIEnvironment, self)._get_units_in_error(status)
        local_unit = hookenv.local_unit()
        return [unit for unit in units if unit != local_unit]
