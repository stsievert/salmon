Experiment initialization
=========================

Experiments can be initialized by vising ``[url]:8421/init_exp``. This supports
the following options:

1. Upload of a `YAML file`_ completely detailing the experiment.
2. Upload of a `YAML file`_ describing experiment, and ZIP file for the targets.
3. Upload of a database dump from Salmon.

"YAML files" must obey a standard; see for a (human-readable) description of
the specification https://learnxinyminutes.com/docs/yaml/. To see if your YAML
is valid, go to https://yamlchecker.com/.

Experiment initialization with YAML file
----------------------------------------

This section will specify the YAML file; including a ZIP file will only modify
the ``targets`` key.

Here's an example YAML file for initialization:

.. code-block:: yaml

   targets: [1, 2, 3, 4, 5]
   instructions: Select the item on the bottom most similar to the item on the top.
   debrief: Thanks! Use the participant ID below in Mechnical Turk.
   max_queries: 25
   samplers:
     RandomSampling: {}
     RoundRobin: {}

The top-level elements like ``max_queries`` and ``targets`` are called "keys"
in YAML jargon. Here's documentation for each key:

* ``targets``, list. Each element will be cast to a string then rendered to
  HTML. Some examples:
    * If ``targets: ["<b>Bold!</b>", "<i>Italic!</i>"]`` is specified, the
      crowdsourcing participant will see bold and italic text in the target.
    * If ``targets: ["<img src='http://....' />", "<img src='http://....'
      />"]`` is specified, the user will see images.
    * If ``targets: ["vonn", "miller", "ligety", "shiffrin"]`` is specified,
      the user will see plain text.
* ``instructions``: text. The instructions for the participant.
* ``debrief``: text. The message to show at the end of the experiment. This
  debrief will show alongside the participant ID (which will be available
  through in the responses).
* ``max_queries``: int. The number of queries a participant should answer. Set
  ``max_queries: -1`` for unlimited queries.
* ``samplers``. See :ref:`adaptive-config` for more detail.


YAML file with ZIP file
-----------------------

If you upload a ZIP file alongside a YAML file, the ``targets`` key above is
configured. Here are the choices for different files to include in the ZIP
file:

- A bunch of images/videos. Support extensions

    - Videos: ``mp4``, ``mov``
    - Images: ``png``, ``gif``, ``jpg``, ``jpeg``

- A single CSV file. Each textual target should be on a new line.

For example, this is a valid CSV file that will render textual targets:

.. code-block::

   Bode Miller
   Lindsey Kildow
   Mikaela Shiffrin
   <b>Ted Ligety</b>
   Paula Moltzan
   Jessie Diggins

Again, every line here is valid HTML, so the crowdsourcing participant will see
bolded text for "**Ted Ligety**." That means we can also render images:

.. code-block::

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
