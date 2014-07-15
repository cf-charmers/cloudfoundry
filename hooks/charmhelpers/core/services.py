import os
import re
from collections import Iterable
from charmhelpers.core import templating
from charmhelpers.core import host
from charmhelpers.core import hookenv


class ServiceManager(object):
    def __init__(self, services=None):
        """
        Register a list of services, given their definitions.

        Traditional charm authoring is focused on implementing hooks.  That is,
        the charm author is thinking in terms of "What hook am I handling; what
        does this hook need to do?"  However, in most cases, the real question
        should be "Do I have the information I need to configure and start this
        piece of software and, if so, what are the steps for doing so."  The
        ServiceManager framework tries to bring the focus to the data and the
        setup tasks, in the most declarative way possible.

        Service definitions are dicts in the following formats (all keys except
        'service' are optional):

            {
                "service": <service name>,
                "required_data": <list of required data contexts>,
                "data_ready": <one or more callbacks>,
                "data_lost": <one or more callbacks>,
                "start": <one or more callbacks>,
                "stop": <one or more callbacks>,
                "ports": <list of ports to manage>,
            }

        The 'required_data' list should contain dicts of required data (or
        dependency managers that act like dicts and know how to collect the data).
        Only when all items in the 'required_data' list are populated are the list
        of 'data_ready' and 'start' callbacks executed.  See `is_ready()` for more
        information.

        The 'data_ready' value should be either a single callback, or a list of
        callbacks, to be called when all items in 'required_data' pass `is_ready()`.
        Each callback will be called with the service name as the only parameter.
        After these all of the 'data_ready' callbacks are called, the 'start'
        callbacks are fired.

        The 'data_lost' value should be either a single callback, or a list of
        callbacks, to be called when a 'required_data' item no longer passes
        `is_ready()`.  Each callback will be called with the service name as the
        only parameter.  After these all of the 'data_ready' callbacks are called,
        the 'stop' callbacks are fired.

        The 'start' value should be either a single callback, or a list of
        callbacks, to be called when starting the service, after the 'data_ready'
        callbacks are complete.  Each callback will be called with the service
        name as the only parameter.  This defaults to
        `[host.service_start, services.open_ports]`.

        The 'stop' value should be either a single callback, or a list of
        callbacks, to be called when stopping the service.  If the service is
        being stopped because it no longer has all of its 'required_data', this
        will be called after all of the 'data_lost' callbacks are complete.
        Each callback will be called with the service name as the only parameter.
        This defaults to `[services.close_ports, host.service_stop]`.

        The 'ports' value should be a list of ports to manage.  The default
        'start' handler will open the ports after the service is started,
        and the default 'stop' handler will close the ports prior to stopping
        the service.


        Examples:

        The following registers an Upstart service called bingod that depends on
        a mongodb relation and which runs a custom `db_migrate` function prior to
        restarting the service, and a Runit serivce called spadesd.

            manager = services.ServiceManager([
                {
                    'service': 'bingod',
                    'ports': [80, 443],
                    'required_data': [MongoRelation(), config(), {'my': 'data'}],
                    'data_ready': [
                        services.template(source='bingod.conf'),
                        services.template(source='bingod.ini',
                                          target='/etc/bingod.ini',
                                          owner='bingo', perms=0400),
                    ],
                },
                {
                    'service': 'spadesd',
                    'data_ready': services.template(source='spadesd_run.j2',
                                                    target='/etc/sv/spadesd/run',
                                                    perms=0555),
                    'start': runit_start,
                    'stop': runit_stop,
                },
            ])
            manager.manage()
        """
        self.services = {}
        for service in services or []:
            service_name = service['service']
            self.services[service_name] = service

    def manage(self):
        """
        Handle the current hook by doing The Right Thing with the registered services.
        """
        hook_name = hookenv.hook_name()
        if hook_name == 'stop':
            self.stop_services()
        else:
            self.provide_data()
            self.reconfigure_services()

    def provide_data(self):
        hook_name = hookenv.hook_name()
        for service in self.services.values():
            for provider in service.get('provided_data', []):
                if re.match(r'{}-relation-(joined|changed)'.format(provider.name), hook_name):
                    data = provider.provide_data()
                    if provider._is_ready(data):
                        hookenv.relation_set(None, data)

    def reconfigure_services(self, *service_names):
        """
        Update all files for one or more registered services, and,
        if ready, optionally restart them.

        If no service names are given, reconfigures all registered services.
        """
        for service_name in service_names or self.services.keys():
            if self.is_ready(service_name):
                self.fire_event('data_ready', service_name)
                self.fire_event('start', service_name, default=[
                    host.service_restart,
                    open_ports])
                self.save_ready(service_name)
            else:
                if self.was_ready(service_name):
                    self.fire_event('data_lost', service_name)
                self.fire_event('stop', service_name, default=[
                    close_ports,
                    host.service_stop])
                self.save_lost(service_name)

    def stop_services(self, *service_names):
        """
        Stop one or more registered services, by name.

        If no service names are given, stops all registered services.
        """
        for service_name in service_names or self.services.keys():
            self.fire_event('stop', service_name, default=[
                close_ports,
                host.service_stop])

    def get_service(self, service_name):
        """
        Given the name of a registered service, return its service definition.
        """
        service = self.services.get(service_name)
        if not service:
            raise KeyError('Service not registered: %s' % service_name)
        return service

    def fire_event(self, event_name, service_name, default=None):
        """
        Fire a data_ready, data_lost, start, or stop event on a given service.
        """
        service = self.get_service(service_name)
        callbacks = service.get(event_name, default)
        if not callbacks:
            return
        if not isinstance(callbacks, Iterable):
            callbacks = [callbacks]
        for callback in callbacks:
            if isinstance(callback, ManagerCallback):
                callback(self, service_name, event_name)
            else:
                callback(service_name)

    def is_ready(self, service_name):
        """
        Determine if a registered service is ready, by checking its 'required_data'.

        A 'required_data' item can be any mapping type, and is considered ready
        if `bool(item)` evaluates as True.
        """
        service = self.get_service(service_name)
        reqs = service.get('required_data', [])
        return all(bool(req) for req in reqs)

    def save_ready(self, service_name):
        """
        Save an indicator that the given service is now data_ready.
        """
        ready_file = '{}/.ready.{}'.format(hookenv.charm_dir(), service_name)
        with open(ready_file, 'a'):
            pass

    def save_lost(self, service_name):
        """
        Save an indicator that the given service is no longer data_ready.
        """
        ready_file = '{}/.ready.{}'.format(hookenv.charm_dir(), service_name)
        if os.path.exists(ready_file):
            os.remove(ready_file)

    def was_ready(self, service_name):
        """
        Determine if the given service was previously data_ready.
        """
        ready_file = '{}/.ready.{}'.format(hookenv.charm_dir(), service_name)
        return os.path.exists(ready_file)


class RelationContext(dict):
    """
    Base class for a context generator that gets relation data from juju.

    Subclasses must provide `interface`, which is the interface type of interest,
    and `required_keys`, which is the set of keys required for the relation to
    be considered complete.  The first relation for the interface that is complete
    will be used to populate the data for template.

    The generated context will be namespaced under the interface type, to prevent
    potential naming conflicts.
    """
    name = None
    interface = None
    required_keys = []

    def __init__(self, *args, **kwargs):
        super(RelationContext, self).__init__(*args, **kwargs)
        self.get_data()

    def __bool__(self):
        """
        Returns True if all of the required_keys are available.
        """
        return self.is_ready()

    __nonzero__ = __bool__

    def __repr__(self):
        return super(RelationContext, self).__repr__()

    def is_ready(self):
        """
        Returns True if all of the `required_keys` are available from any units.
        """
        ready = len(self.get(self.name, [])) > 0
        if not ready:
            hookenv.log('Incomplete relation: {}'.format(self.__class__.__name__), hookenv.DEBUG)
        return ready

    def _is_ready(self, unit_data):
        """
        Helper method that tests a set of relation data and returns True if
        all of the `required_keys` are present.
        """
        return set(unit_data.keys()).issuperset(set(self.required_keys))

    def get_data(self):
        """
        Retrieve the relation data for each unit involved in a realtion and,
        if complete, store it in a list under `self[self.name]`.  This
        is automatically called when the RelationContext is instantiated.

        The units are sorted lexographically first by the service ID, then by
        the unit ID.  Thus, if an interface has two other services, 'db:1'
        and 'db:2', with 'db:1' having two units, 'wordpress/0' and 'wordpress/1',
        and 'db:2' having one unit, 'mediawiki/0', all of which have a complete
        set of data, the relation data for the units will be stored in the
        order: 'wordpress/0', 'wordpress/1', 'mediawiki/0'.

        If you only care about a single unit on the relation, you can just
        access it as `{{ interface[0]['key'] }}`.  However, if you can at all
        support multiple units on a relation, you should iterate over the list,
        like:

            {% for unit in interface -%}
                {{ unit['key'] }}{% if not loop.last %},{% endif %}
            {%- endfor %}

        Note that since all sets of relation data from all related services and
        units are in a single list, if you need to know which service or unit a
        set of data came from, you'll need to extend this class to preserve
        that information.
        """
        if not hookenv.relation_ids(self.name):
            return

        ns = self.setdefault(self.name, [])
        for rid in sorted(hookenv.relation_ids(self.name)):
            for unit in sorted(hookenv.related_units(rid)):
                reldata = hookenv.relation_get(rid=rid, unit=unit)
                if self._is_ready(reldata):
                    ns.append(reldata)

    def provide_data(self):
        """
        Return data to be relation_set for this interface.
        """
        return {}

    @classmethod
    def remote_view(cls):
        """
        Return the provided relation data as it would be seen by a remote unit.
        """
        inst = cls()
        return {inst.name: [inst.provide_data()]}


class ManagerCallback(object):
    """
    Special case of a callback that takes the `ServiceManager` instance
    in addition to the service name.

    Subclasses should implement `__call__` which should accept two parameters:

        * `manager`       The `ServiceManager` instance
        * `service_name`  The name of the service it's being triggered for
        * `event_name`    The name of the event that this callback is handling
    """
    def __call__(self, manager, service_name, event_name):
        raise NotImplementedError()


class TemplateCallback(ManagerCallback):
    """
    Callback class that will render a template, for use as a ready action.

    The `target` param, if omitted, will default to `/etc/init/<service name>`.
    """
    def __init__(self, source, target, owner='root', group='root', perms=0444):
        self.source = source
        self.target = target
        self.owner = owner
        self.group = group
        self.perms = perms

    def __call__(self, manager, service_name, event_name):
        service = manager.get_service(service_name)
        context = {}
        for ctx in service.get('required_data', []):
            context.update(ctx)
        templating.render(self.source, self.target, context,
                          self.owner, self.group, self.perms)


class PortManagerCallback(ManagerCallback):
    """
    Callback class that will open or close ports, for use as either
    a start or stop action.
    """
    def __call__(self, manager, service_name, event_name):
        service = manager.get_service(service_name)
        new_ports = service.get('ports', [])
        port_file = os.path.join(hookenv.charm_dir(), '.{}.ports'.format(service_name))
        if os.path.exists(port_file):
            with open(port_file) as fp:
                old_ports = fp.read().split(',')
            for old_port in old_ports:
                if bool(old_port):
                    old_port = int(old_port)
                    if old_port not in new_ports:
                        hookenv.close_port(old_port)
        with open(port_file, 'w') as fp:
            fp.write(','.join(str(port) for port in new_ports))
        for port in new_ports:
            if event_name == 'start':
                hookenv.open_port(port)
            elif event_name == 'stop':
                hookenv.close_port(port)


# Convenience aliases
render_template = template = TemplateCallback
open_ports = PortManagerCallback()
close_ports = PortManagerCallback()
