
.. _init:

Experiment initialization
=========================

Throughout the documentation, the YAML file for initialization will be referred
to as ``init.yaml``.

.. note::

   This method is required even if images/videos are includes in a ZIP file (as
   described in :ref:`yaml_plus_zip`). Uploading a ZIP file only modifies the
   ``targets`` "key" in the YAML file.

Now, let's describe three methods on how to launch this experiment:

.. _yamlinitialization:

Experiment initialization with YAML file
----------------------------------------

"YAML files" must obey a standard; see for a (human-readable) description of
the specification https://learnxinyminutes.com/docs/yaml/. To see if your YAML
is valid, go to https://yamlchecker.com/.  Here's an example ``init.yaml`` YAML
file for initialization:

.. code-block:: yaml

   # file: init.yaml
   targets: ["l", "<i>kildow</i>", "t", "<i>ligety</i>"]  # or uploaded via ZIP file
   html:
     instructions: Select the item on the bottom most similar to the item on the top.
     debrief: Thanks! Use the participant ID below in Mechnical Turk.
     max_queries: 100


This file will initialize a basic experiment. By default, Salmon will do the
following:

* **Use random sampling.** This is a very simple configuration -- but it may
  not be what you want. Relevant FAQs:

  * ":ref:`random_vs_active`"
  * ":ref:`adaptiveconfig`" This FAQ links to :ref:`alg-config`.

* Ask 50 questions before showing the participant ID.
* Embed into :math:`d=2` dimensions if active samplers are specified.

More documentation on customizing these fields can be found in
:ref:`alg-config` and :ref:`frontendcustomization`, and the defaults for
instructions/debrief can be found in :class:`~salmon.triplets.manager.HTML`. To
do anything fancier, additional configuration is required. Here's a basic
example:

.. code-block:: yaml

   # file: init.yaml
   targets: ["l", "<i>kildow</i>", "t", "<i>ligety</i>"]  # or uploaded via ZIP file
   html:
     max_queries: 100
   samplers:
     ARR: {"random_state": 42}
     Random: {}
   sampling:
     probs: {"ARR": 85, "Random": 15}
     common:
       d: 3  # embed into 3 dimensions for all active samplers

The ``samplers`` controls which methods get to choose queries, and ``sampling``
controls how multiple samplers interact (i.e., how should a sampler be chosen?)
More documentation can be found at :ref:`alg-config`.

Complete details on the YAML file are at at
:class:`~salmon.triplets.manager.Config`. Examples of these files are in
`salmon/examples`_. A complete example is available at
`salmon/examples/complete.yaml`_.

.. _salmon/tests/data: https://github.com/stsievert/salmon/tree/master/tests/data
.. _salmon/examples: https://github.com/stsievert/salmon/tree/master/examples
.. _salmon/examples/complete.yaml: https://github.com/stsievert/salmon/tree/master/examples/complete.yaml

.. _yaml_plus_zip:

YAML file with ZIP file
-----------------------

Uploading a ZIP file for targets/stimuli is a small addition to
":ref:`yamlinitialization`." The only difference is that uploading a ZIP file
overwrites and configures the ``targets`` key for you (so it's not necessary to
specify the ``targets`` key when uploading a ZIP file).

Here are the choices for different files to include in the ZIP file:

- A single CSV file. Each textual target should be on a new line.
- A bunch of images/videos. Support extensions:

  - Videos: ``mp4``, ``mov``
  - Images: ``png``, ``gif``, ``jpg``, ``jpeg``


A YAML file must be uploaded describing the experiment in addition to including
the targets in the ZIP file.  Let's walk through two examples, both with
uploading a bunch of images with skiers. Both cases will use this ``init.yaml``
file:

.. code-block:: yaml

  # file: init.yaml
  html:
    instructions: >  # multi-line YAML string
        Select the <i>comparison</i> item on the bottom that
        is most similar to the <i>target</i> item on the top.
    debrief: <b>Thanks!</b> Use the participant ID below in Mechanical Turk.
    max_queries: 100

.. note::

   Uploading a ZIP file completely replaces any specification of the
   ``targets`` key above. This means that it is not necessary to specify the
   ``targets`` key when a ZIP file is uploaded because it will be specified
   automatically.

Images/videos
^^^^^^^^^^^^^

If I had all these images in a ZIP file (say ``skiers.zip``), I would gather
all the images into a ZIP file. On macOS, that's possible by selecting all the
images then control-clicking and selecting "Compress items." On the command
line, the command ``zip targets.zip *.jpg *.png`` will collect all JPG/PNG
images into ``targets.zip``.

Text targets
^^^^^^^^^^^^

This is a valid CSV file that will render textual targets:

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
is, at ``http://[url]:8421/dashboard``). This will download a file called
``exp-[date]-vX.Y.Z.rdb``. Do not delete the numbers ``X.Y.Z``!

Salmon supports the upload of this file to the same version of Salmon. The
upload of this file will restore the state of your experiment. After this file
is uploaded, the two machines will become indistinguishable from each other
(which allows you to download the entire experiment onto your own machine then
upload it to a completely new machine a month later and start collecting
responses again).

If you run into errors, the FAQ ":ref:`restorefrombackupfaq`" will likely be
relevant.
