.. _getting-started:

Starting an experiment
======================

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

Experiment initialization
-------------------------
After a user has been successfully created, hit the back
button and launch an experiment. You have three options:

1. Upload of a YAML file completely detailing the experiment.
2. Upload of a YAML file describing experiment, and ZIP file for the targets.
3. Upload of a database dump from Salmon.

These options will be detailed below. Throughout the documentation, the YAML
file for initialization will be referred to as ``init.yaml``.

After you launch your experiment and vist ``http://[url]:8421``, you will see a query
page:

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

Now, let's describe three methods on how to launch this experiment:

Experiment initialization with YAML file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section will specify the YAML file; including a ZIP file will only modify
the ``targets`` key.

"YAML files" must obey a standard; see for a (human-readable) description of
the specification https://learnxinyminutes.com/docs/yaml/. To see if your YAML
is valid, go to https://yamlchecker.com/.


Here's an example ``init.yaml`` YAML file for initialization:

.. code-block:: yaml

   # file: init.yaml
   targets: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
   instructions: Select the item on the bottom most similar to the item on the top.
   debrief: Thanks! Use the participant ID below in Mechnical Turk.
   max_queries: 100
   samplers:
     ARR: {}
     RandomSampling: {}
   sampling:
     probs: {"ARR": 80, "RandomSampling": 20}

The top-level elements like ``max_queries`` and ``targets`` are called "keys"
in YAML jargon. Here's documentation for each key:

* ``instructions``: text. The instructions for the participant.
* ``debrief``: text. The message to show at the end of the experiment. This
  debrief will show alongside the participant ID (which will be available
  through in the responses).
* ``max_queries``: int. The number of queries a participant should answer. Set
  ``max_queries: -1`` for unlimited queries.
* ``samplers``. See :ref:`adaptive-config` for more detail.
* ``sampling``. A dictionary with the key ``probs`` and percentage
  probabilities for each algorithm.
* ``targets``, optional list. Choices:

    * YAML list. This ``targets: ["vonn", "miller", "ligety", "shiffrin"]`` is
      specified, the user will see plain text. If this text includes HTML, it
      will be rendered. For example if one target is ``"<i>kildow</i>"`` the
      user will see italic text when that target is displayed.

    * Don't include the ``targets`` keyword and upload a ZIP file instead. This
      will completely replace ``targets`` with the default renderings of the
      contents of the ZIP file (detailed in the next section).

* ``skip_button``, optional boolean. Default ``false``. If ``true``, show a
  button that says "new query."
* ``css``, optional string. Defaults to ``""``. This CSS is inserted in the
  ``<style>`` tag in the HTML query page. This allows customization of
  colors/borders/etc.

Examples of these files are in `salmon/tests/data`_ and `salmon/examples`_.

.. _salmon/tests/data: https://github.com/stsievert/salmon/tree/master/tests/data
.. _salmon/examples: https://github.com/stsievert/salmon/tree/master/examples

YAML file with ZIP file
^^^^^^^^^^^^^^^^^^^^^^^

If you upload a ZIP file alongside the ``init.yaml`` YAML file, the ``targets``
key above will be configured to represent each object in the ZIP file. Here are
the choices for different files to include in the ZIP file:

- A bunch of images/videos. Support extensions

    - Videos: ``mp4``, ``mov``
    - Images: ``png``, ``gif``, ``jpg``, ``jpeg``

- A single CSV file. Each textual target should be on a new line.

For example, this is a valid CSV file that will render textual targets:

.. code-block::

   # file: targets.csv. Zipped into targets.csv.zip and uploaded.
   Bode Miller
   Lindsey Kildow
   Mikaela Shiffrin
   <b>Ted Ligety</b>
   Paula Moltzan
   Jessie Diggins

Again, every line here is valid HTML, so the crowdsourcing participant will see
bolded text for "**Ted Ligety**." That means we can also render images:

.. code-block::

   # file: targets.csv. Zipped into targets.csv.zip and uploaded.
   <img width="300px" src="https://upload.wikimedia.org/wikipedia/commons/3/30/Bode_Miller_at_the_2010_Winter_Olympic_downhill.jpg" />
   <img width="300px" src="https://upload.wikimedia.org/wikipedia/commons/8/89/Miller_Bode_2008_002.jpg" />
   <img width="300px" src="https://upload.wikimedia.org/wikipedia/commons/5/5e/Lindsey_Kildow_Aspen.jpg" />
   <img width="300px" src="https://commons.wikimedia.org/wiki/File:Michael_Sablatnik_Slalom_Spital_am_Semmering_2008.jpg" />
   <img width="300px" src="https://upload.wikimedia.org/wikipedia/commons/e/e9/Kjetil_Jansrud_giant_slalom_Norway_2011.jpg" />

One rendered target will be this image:

.. raw:: html

   <img width="300px" src="https://upload.wikimedia.org/wikipedia/commons/8/89/Miller_Bode_2008_002.jpg" />

Database dump
^^^^^^^^^^^^^

The dashboard offers a link to download the experiment on the dashboard (that
is, at ``http://[url]:8421/dashboard``). This will download a file called
``exp-[date]-vX.Y.Z.rdb``. Do not delete the numbers ``X.Y.Z``!

Salmon supports the upload of this file to the same version of Salmon. The
upload of this file will restore the state of your experiment.

Send the URL to participants
----------------------------

The URL to send to the crowdsourcing participants is ``http://[url]:8421/``.
For example, that may be

.. code::

   http://ec2-52-204-122-132.compute-1.amazonaws.com:8421/init

Typically, paid services like Mechantical Turk are used to recruit
crowdsourcing participants. Reddit and email have been used for unpaid
recruitment.
