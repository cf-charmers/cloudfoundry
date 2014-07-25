==================
CF Charm Generator
==================

.. image:: https://badge.fury.io/py/charmgen.png
    :target: http://badge.fury.io/py/charmgen

.. image:: https://travis-ci.org/bcsaller/charmgen.png?branch=master
        :target: https://travis-ci.org/bcsaller/charmgen

.. image:: https://pypip.in/d/charmgen/badge.png
        :target: https://pypi.python.org/pypi/charmgen


A Juju charm to generate CF charms from metadata and
manage them at runtime.

* Free software: BSD license
* Documentation: http://charmgen.readthedocs.org.

Development
-----------

For any given release we support (see cloudfoundry.releases) you should be able
to generate an example of the bundle we'll deploy and manage by doing:

    . .tox/py27/bin/activate
    python charmgen.generator <release>

This will create a cloudfoundry-r<release> directory with the bundle.yaml and a
trusty repo will all the created charms.

There are currently two experimental tools included with the charm. These
are designed to process a cf-release checkout and examine the differences
in various tagged versions of cf-release.

    . .tox/py27/bin/activate
    # skip if you have a cf-release checkout
    git clone https://github.com/cloudfoundry/cf-release.git ../cf-release
    python setup.py develop
    get_revisions -d ../cf-release 153..173
    diff_revisions 153..173 | less

You can also use the following command on the cc unit to monitor the routes
registered with NATS, which can be very helpful for debugging:

    cd /var/vcap/packages/cloud_controller_ng/cloud_controller_ng/vendor/bundle/ruby/1.9.1
    /var/vcap/packages/ruby/bin/bundle exec bin/nats-sub -s nats://<nats-user>:<nats-pass>@<nats-internal-addr>:4222 ">"




* TODO

  Attempt to generate service definitions and relation classes from
  cf-release.
