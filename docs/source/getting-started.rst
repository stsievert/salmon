.. _getting-started:

Getting started
===============

Launching an experiment to crowdsourcing participants requires following this
process:

1. Visiting ``http://[url]:8421/init`` with the ``[url]`` from
   :ref:`installation`.
2. Creating a username/password
3. Launching an experiment.
4. Sending the URL ``http://[url]:8421/`` to crowdsourcing participants.


Initialization page
-------------------

By default, Salmon does not support HTTPS. Make sure the URL begins with
``http://``, not ``https://``. For example, the URL you visit may look like:

.. code::

   http://ec2-52-204-122-132.compute-1.amazonaws.com:8421/init

Username/password
-----------------

When visiting ``http://[url]:8421/init``, first, type a username/password and
hit "create user."

.. warning::

   Do not lose this username/password! You need the username/password to view
   the dashboard and download the received responses.

.. warning::

   Once a username/password are set, they can not be changed. The
   username/password will remain the same when Salmon is reset and when the
   machine Salmon is running on is restarted.

It is technically possible to recover the username/password with the key file
``key.pem`` that Amazon AWS provides and the URL above:

.. code-block:: shell

   (personal) $ ssh -i key.pem ubuntu@[url]
   (ec2) $ cat /home/ubuntu/salmon/creds.json


Experiment initialization
-------------------------

After a user has been successfully created, hit the back
button and launch an experiment. You have three options:

1. Upload of a YAML file completely detailing the experiment.
2. Upload of a YAML file describing experiment, and ZIP file for the targets.
3. Upload of a database dump from Salmon.

These options are detailed at ":ref:`init`." After you launch your experiment
and vist ``http://[url]:8421``, you will see a query page:

.. _YAML specification: https://yaml.org/

.. image:: imgs/query_page.png
   :align: center
   :width: 500px

.. note::

   This image is almost certainly out of date.

.. note::

   Please include the version in any bug reports or feature requests.
   The version number is available at ``http://[url]:8421/docs`` and should look
   something like ``v0.4.1``, typically shown right next to "Salmon."

Send the URL to participants
----------------------------

The URL to send to the crowdsourcing participants is ``http://[url]:8421/``.
For example, that may be

.. code::

   http://ec2-52-204-122-132.compute-1.amazonaws.com:8421/init

Typically, paid services like Mechantical Turk are used to recruit
crowdsourcing participants. Reddit and email have been used for unpaid
recruitment.
