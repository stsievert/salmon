.. _installation:

Installation
============

This pages details how to get Salmon running, either on EC2 or locally on your
machine. After you get Salmon running, detail on how to launch experiments in
:ref:`getting-started`.

.. note::

   See the `Troubleshooting`_ section if you're having difficulties with either
   of the processes below.

.. _Salmon's issue tracker: https://github.com/stsievert/salmon/issues

Experimentalist
---------------

1. Sign into Amazon AWS (http://aws.amazon.com/)
2. Select the "Oregon" region (or ``us-west-2``) in the upper right.
3. Go to Amazon EC2.
4. Launch a new instance (the big blue button or square orange button).
5. Select AMI ``ami-07d9e17b8dea4da43`` titled "Salmon".

    * Note: the AMI appears in Community AMIs after searching "Salmon"
      (only in the Oregon/``us-west-2`` region!).

6. Select an appropriate instance type.

    * Salmon requires at least 2GB of memory and 1 CPU.
    * ``t3.large`` is recommended for passive algorithms (i.e, random
      sampling).
    * ``t3.xlarge`` is recommended for adaptive algorithms (e.g., ARR; see the
      :ref:`benchmarks on adaptive algorithm <experiments>` for more detail).
    * Note: https://ec2instances.info/ is a great resource to check costs.
      As of April 2022, ``t3.large`` and ``t3.xlarge`` cost about $2/day and $4/day respectively.

7. Create a key pair.

    .. warning::

       **Don't lose your key pair!**
       Without the key pair, the Salmon developers will be severely
       limited in the help they can provide.

8. Don't click the big orange button yet. Continue to the rules page, and add
   these rules:

    1. In the networking interface box, check the HTTP and HTTP boxes
       and select the "edit" button:

       .. image:: imgs/network-http-rules.png
          :width: 80%
          :align: center

    2. After hitting "edit", scroll down to "add security group rule"
       and open port 8421 to ``0.0.0.0/0`` (aka anyone).

       .. image:: imgs/network-rule.png
          :width: 80%
          :align: center

9. Now, click the big orange button! The AMI will probably take around
   15 to initialize (but may take up to 30 minutes).
10. Keep your "key pair" in a safe place. The key pair typically has a
    ``.pem`` extension.

The AMI initialization is done (which takes about 15 minutes), Salmon will be
available at ``http://[url]:8421``. For example, ``[url]`` might be the Amazon
public DNS or public IP.

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

.. note::

   The storage required for Salmon is 128GB. According to `Amazon's EBS
   pricing`_, that costs about $10/month (in April 2022).

.. _Amazon's EBS pricing: https://aws.amazon.com/ebs/pricing/

.. _list of Salmon releases: https://github.com/stsievert/salmon/releases

.. _local-install:

Local install
-------------

See :ref:`offlineinstall` for the process of installing locally.


.. _troubleshooting:

Troubleshooting
---------------

See :ref:`faq` for more general questions.

.. note::

   Please include the version in any bug reports or feature requests.  The
   version number should look something like ``v0.4.1``. It can be found at
   ``http://[url]:8421/docs`` or in the downloaded experiment file (found at
   ``http://[url]:8421/download`` which has a filename like
   ``exp-2021-05-20T07:31-salmon-v0.4.1.rdb``).


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

.. _restorefrombackupfaq:

Restoring from a backup didn't work
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This might happen if Salmon changed between when you downloaded and tried to
restore the experiment. Launching from EC2 always downloads the latest version
of Salmon, which may not work with your backup file.

.. note::

   Salmon follows `semantic software versioning`_. If the version string in the
   .rdb file takes the form ``vA.B.C``, then:

   * The backup is guaranteed to work if `the latest release`_ has version
     ``vA.B.C``.
   * The backup will almost certainly work if `the latest release`_ has version
     ``vA.B.*``.
   * The backup `might` work if `the latest release`_ has version ``vA.*.*``.

   Uploading backup files when `relevant` "backwards incompatible" software
   changes are made, which should be encoded in the release notes.

So, it uploading your backup did not work (it should if the version numbers are
correct), let's launch the correct version of Salmon's server on your machine. That requires this process:

1. Get the correct version of Salmon.
2. Spin up a Salmon server.
3. Go to ``http://localhost:8421/init``
4. Upload the ``.rdb`` file to restore.

This process is basically "launch Salmon's server on your machine."
First, let's get the right version of Salmon:

.. code-block:: shell

   $ # Get right version of Salmon
   $ git clone https://github.com/stsievert/salmon.git
   $ cd salmon
   $ git checkout v0.7.0  # from .rdb filename; will take the form "vA.B.C" or "vA.B.CrcD"

Second, let's launch Salmon:

.. code-block:: shell

   $ docker-compose up  # takes a while
   $ # visit http://localhost:8421/init

**Now re-upload the file using the interface at the bottom of the screen.**

Now Salmon will issue instructions to restart. Let's do that:

.. code-block:: shell

   $ # Now, let's follow the directions Salmon gave:
   $ docker-compose stop; docker-compose start
   $ docker-compose logs -f
   $ # visit http://localhost:8421/dashboard


.. _semantic software versioning: https://semver.org/
.. _the latest release: https://github.com/stsievert/salmon/releases
