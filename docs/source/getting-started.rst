.. _getting-started:

Starting an experiment
======================

Experiments can be initialized by vising ``[url]:8421/init_exp``. This supports
the following options:

1. Upload of a YAML file completely detailing the experiment.
2. Upload of a YAML file describing experiment, and ZIP file for the targets.
3. Upload of a database dump from Salmon.

Through the documentation, the YAML file for initialization will be referred to
as ``init.yaml``.

"YAML files" must obey a standard; see for a (human-readable) description of
the specification https://learnxinyminutes.com/docs/yaml/. To see if your YAML
is valid, go to https://yamlchecker.com/.

After you launch your experiment and vist ``[url]:8421``, you will see a query
page:

.. _YAML specification: https://yaml.org/

.. image:: imgs/query_page.png
   :align: center
   :width: 500px

.. note::

   This image is almost certainly out of date.

.. warning::

   Please include the version in any bug reports or feature requests.
   The version number is available at ``[url]:8421/docs`` and should look
   something like ``v0.4.1``, typically shown right next to "Salmon."

Now, let's describe three methods on how to launch this experiment:

Experiment initialization with YAML file
----------------------------------------

This section will specify the YAML file; including a ZIP file will only modify
the ``targets`` key.

Here's an example ``init.yaml`` YAML file for initialization:

.. code-block:: yaml

   # file: init.yaml
   targets: [1, 2, 3, 4, 5]
   instructions: Select the item on the bottom most similar to the item on the top.
   debrief: Thanks! Use the participant ID below in Mechnical Turk.
   max_queries: 25
   samplers:
     RandomSampling: {}
     RoundRobin: {}

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
-----------------------

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
-------------

The dashboard offers a link to download the experiment on the dashboard (that
is, at ``[url]:8421/dashboard``). This will download a file called
``dump-X.Y.Z.rdb``. Do not delete the numbers ``X.Y.Z``!

Salmon supports the upload of this file to the same version of Salmon. The
upload of this file will restore the state of your experiment.
