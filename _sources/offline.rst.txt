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

This section has two dependencies:

1. Git for the ``git`` command. `Git-SCM`_ has a good installation guide.
2. The ``conda`` package manager, available through Anaconda with their
   `Anaconda Python Distribution`_ or their (much smaller) `Miniconda`_.

.. _Anaconda Python Distribution: https://www.anaconda.com/products/distribution#Downloads
.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html
.. _Git-SCM: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

To install Salmon, these commands should be run:

.. code-block:: shell

   $ git clone https://github.com/stsievert/salmon
   $ cd salmon
   $
   $ # latest release (/tag in git parlance)
   $ latestRelease=$(git describe --tags `git rev-list --tags --max-count=1`)
   $ git checkout $latestRelease
   $
   $ conda env create -f salmon.yml
   $ conda activate salmon
   (salmon) $ pip install -e .

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

   from salmon.triplets.offline import OfflineEmbedding

   df = pd.read_csv("responses.csv")  # from dashboard
   X = df[["head", "winner", "loser"]].to_numpy()

   em = pd.read_csv("embedding.csv")  # from dashboard

   n = int(X.max() + 1)  # number of targets
   d = 2  # embed into 2 dimensions

   X_train, X_test = train_test_split(X, random_state=42, test_size=0.2)
   model = OfflineEmbedding(n=n, d=d, max_epochs=500_000)
   model.initialize(X_train, embedding=em.to_numpy())

   model.fit(X_train, X_test)

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
