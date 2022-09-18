Generating embeddings offline
=============================

Salmon is good at asking useful questions to crowdsourcing participants.

These responses should be used to create an embedding *offline.* Yes, Salmon
has to generate an embedding to determine which questions are useful... but
that shouldn't be the final embedding used for downstream analysis.

This documentation page will step through the process required to generate the
embedding:

1. Download responses and experiment
2. Install Salmon on your own machine.
3. Generate embedding.

Downloading responses
---------------------

Download the responses, either by visiting ``http://[url]:8421/responses`` or
clicking the link on the dashboard (as mentioned in :ref:`exp-monitoring`).

Install Salmon
--------------

There are two options to install Salmon for offline embeddings.

Option 1: Using pip
^^^^^^^^^^^^^^^^^^^

This option is recommended to generate embeddings offline.  This option
requires ``pip``, a Python package manager. It's available through `Anaconda`_
and `Miniconda`_.


1. Run the command ``pip install salmon-triplets``.
2. Run the command below in Python to verify that the installation worked successfully:

.. code-block:: python

   from salmon.triplets.offline import OfflineEmbedding

.. note::

   This package named "salmon-triplets" on PyPI installs a Python package
   named ``salmon``.

Option 2: Using conda
^^^^^^^^^^^^^^^^^^^^^

This option is required for a complete installation.  This option requires
``conda``, a Anaconda's Python package manager. It's available through
`Anaconda`_ and `Miniconda`_.

1. Download `the latest release of Salmon`_, and unpack the `.zip` or `.tar.gz`
   file.
2. Navigate to the directory in the shell/terminal and run these commands:

.. code-block:: shell

   $ # download salmon-X.Y.Z.zip into ~/Downloads
   $ # unzip/untar into directory `salmon`
   $ # then navigate there in your shell/Terminal
   $ cd ~/Downloads/salmon
   $ conda env create -f salmon.yml
   $ conda activate salmon
   (salmon) $ pip install .

.. _the latest release of Salmon: https://github.com/stsievert/salmon/releases/latest
.. _Anaconda: https://www.anaconda.com/products/distribution#Downloads
.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html

These commands should be run in your favorite terminal. On macOS, that might
be Terminal.app.

.. note::

   The commands above are (\*nix) shell commands. The ``$`` is intended to
   be your terminal prompt; leave it out when copy and pasting into the
   terminal.

Generate embeddings
-------------------

This Python code will generate an embedding:

.. code-block:: python

   import pandas as pd
   from sklearn.model_selection import train_test_split

   from salmon.triplets.offline import OfflineEmbedding

   # Read in data
   df = pd.read_csv("responses.csv")  # from dashboard
   em = pd.read_csv("embedding.csv")  # from dashboard; optional

   X = df[["head", "winner", "loser"]].to_numpy()
   X_train, X_test = train_test_split(X, random_state=42, test_size=0.2)

   n = int(X.max() + 1)  # number of targets
   d = 2  # embed into 2 dimensions

   # Fit the model
   model = OfflineEmbedding(n=n, d=d, max_epochs=500_000)
   model.initialize(X_train, embedding=em.to_numpy())  # (optional)

   model.fit(X_train, X_test)

   # Inspect the model
   model.embedding_  # embedding
   model.history_  # to view information on how well train/test performed

Some customization can be done with ``model.history_``; it may not be necessary
to train for 500,000 epochs. ``model.history_`` will include validation and
training scores, which might help limit the number of epochs.

Documentation for :class:`~salmon.triplets.offline.OfflineEmbedding` is
available on :ref:`api`.

Embedding visualization
-----------------------

The HTML for each target alongside the embedding coordinates is available from
the dashboard by downloading the "embeddings" file (or visiting
``[url]:8421/embeddings``. This will give a CSV with the HTML for each target,
the embedding coordinates and the name of the embedding that generated the
algorithm.

To visualize the embedding, standard plotting tools can be used to visualize
the embedding, which might be `Matplotlib`_, the `Pandas visualization API`_,
`Bokeh`_ or `Altair`_. The Pandas visualization API is likely the easiest to
use, but won't support showing HTML (images/video/etc). To do that, Salmon uses
Bokeh for it's visualization.


.. _Pandas visualization API: https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html
.. _Bokeh: https://bokeh.org/
.. _Matplotlib: https://matplotlib.org/
.. _Altair: https://altair-viz.github.io/
