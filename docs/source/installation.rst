Installation
============

This pages details how to get Salmon running, either on EC2 or locally on your
machine. After you get Salmon running, detail on how to launch experiments in
:ref:`getting-started`.

Experimentalist
---------------

1. Sign into Amazon AWS (http://aws.amazon.com/)
2. Select the "Oregon" region (or ``us-west-2``) in the upper right.
3. Go to Amazon EC2
4. Launch a new instance (the big blue button or square orange button).
5. Select AMI ``ami-0e3134e3437ec5b85`` titled "Salmon". It appears in
   Community AMIs after searching "Salmon".
6. Select an appropriate instance type.

    * ``t3.large`` is recommended for passive algorithms (i.e, random sampling).
    * ``t3.xlarge`` is recommended for adaptive algorithms (e.g, TSTE).
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

- ``http://[url]:8421/init_exp`` to initialize an experiment
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
On your local machine as a developer? Run this following code in a terminal:

.. code:: shell

   $ git clone https://github.com/stsievert/salmon.git

First, `install Docker`_ and `install Git`_. After that, run the following code:

.. _install Docker: https://www.docker.com/products/docker-desktop
.. _install Git: https://git-scm.com/downloads

.. code:: shell

   $ cd salmon
   $ docker-compose build
   $ docker-compose up
   $ # visit http://localhost:8421/init_exp or http://localhost:8421/docs

Developer
---------
Follow the instructions for local machine launch.

If you make changes to this code, follow these instructions:

.. code:: shell

	$ docker-compose stop
	$ docker-compose build
	$ docker-compose up
