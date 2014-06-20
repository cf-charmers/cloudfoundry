===============================
CF Charm Generator
===============================

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



* TODO
