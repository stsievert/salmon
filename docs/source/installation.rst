.. _installation:

Installation
============

This pages details how to get Salmon running, either on EC2 or locally on your
machine. After you get Salmon running, detail on how to launch experiments in
:ref:`getting-started`.

.. note::

   See the `Troubleshooting`_ section if you're having difficulties with either
   of the processes below.

Experimentalist
---------------

1. Sign into Amazon AWS (http://aws.amazon.com/)
2. Select the "Oregon" region (or ``us-west-2``) in the upper right.
3. Go to Amazon EC2.
4. Launch a new instance (the big blue button or square orange button).
5. Select AMI ``ami-0e3134e3437ec5b85`` titled "Salmon". It appears in
   Community AMIs after searching "Salmon".
6. Select an appropriate instance type.

    * ``t3.large`` is recommended for passive algorithms (i.e, random
      sampling).
    * ``t3.xlarge`` is recommended for adaptive algorithms (e.g., ARR; see the
      :ref:`benchmarks on adaptive algorithm <experiments>` for more detail).
    * (note: https://ec2instances.info/ is a great resource to check costs)

7. Don't click the big blue button yet. Continue to the rules page, and add
   these rules:

.. image:: imgs/networking-rule.png
   :width: 80%
   :align: center

The AMI will take about 15 minutes to initialize. After that's done, Salmon
will be available at ``http://[url]:8421``. For example, ``[url]`` might be
the Amazon public DNS or public IP.

.. code::

   http://ec2-35-164-240-184.us-west-2.compute.amazonaws.com:8421/foo

.. warning::

   By default, Salmon does not support HTTPS. Be sure the URL begins with
   ``http://`` and not ``https://``!

Until you upload data, ``http://[url]:8421`` will only show an error message.
To start using Salmon, these endpoints will be available:

- ``http://[url]:8421/init`` to create a user and initialize a new experiment.
- ``http://[url]:8421/docs`` to see the endpoint documentation. The Salmon
  version displayed should match the most recent Salmon release in the `list of
  Salmon releases`_.
- ``http://[url]:8421/dashboard`` to view all relevant links, including links
  to the...

  * The **query page.** This is the URL that shows the relevant triplets. This
    is the URL to be sent to a crowdsourcing service.
  * **API documentation**. This includes information on how to launch an
    experiment, and what files need to be uploaded. View the documentation for
    the POST request ``/init_exp`` for more detail.
  * **Download the experiment.** The downloaded file can be re-uploaded to a
    new machine so experiments can be restarted.
  * **Responses**. To get all human responses.
  * **Logs**. This is very useful for debugging.

  .. warning::

     Download all files when stopping or terminating the machine -- especially
     the responses and experiment file.

.. note::

   If you have an issue with the machine running Salmon, be sure to include the
   logs when contacting the Salmon developers. They'd also appreciate it if
   you left the machine running.


.. _list of Salmon releases: https://github.com/stsievert/salmon/releases

Local machine
-------------

This process is meant for developers. To launch, first download the code.  It's
possible to download `a ZIP file of Salmon's source`_, or if Git is installed,
to run this command:

.. _a ZIP file of Salmon's source: https://github.com/stsievert/salmon/archive/refs/heads/master.zip

.. code:: shell

   $ git clone https://github.com/stsievert/salmon.git

Then, to launch a local version of Salmon you'll need `Docker Compose`_.
After that dependency is intalled, run the following code:

.. _install Docker: https://www.docker.com/products/docker-desktop
.. _install Git: https://git-scm.com/downloads

.. code:: shell

   $ cd salmon
   $ docker-compose build
   $ docker-compose up
   $ # visit http://localhost:8421/init or http://localhost:8421/docs

.. _Docker Compose: https://docs.docker.com/compose/install/

If you make changes to this code, run these commands:

.. code:: shell

	$ docker-compose stop
	$ docker-compose build
	$ docker-compose up

If you run the command ``export SALMON_DEBUG=1``, the Salmon server will watch
for changes in the source and re-launch as necessary. This won't be perfect,
but it will reduce the number of times required to run ``docker-compose {stop,
build, up}``.

If you run the command ``export SALMON_NO_AUTH=1``, the Salmon server will
not require a username/password.

.. _troubleshooting:

Troubleshooting
---------------

See :ref:`faq` for more general questions.

I can't access Salmon's URL
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Try using ``http://`` instead of ``https://``.  By default, EC2 does not
support HTTPS, and some browsers use HTTPS automatically.

I can't find Salmon's AMI
^^^^^^^^^^^^^^^^^^^^^^^^^

Are you in EC2's Oregon region, ``us-west-2``? That can be changed in the upper
right of the Amazon EC2 interface.

The Salmon AMI has been created in the ``us-west-2`` region, and EC2 AMIs are
only available in the regions they're created in.

The Docker machines aren't launching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Are you using the command ``docker-compose up`` to launch Salmon? The command
``docker build .`` doesn't work.

Salmon requires a Redis docker machine and certain directories/ports being
available. Technically, it's possible to build all the Docker machines
yourself (but it's not feasible).
