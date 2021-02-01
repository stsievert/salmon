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
Download the responses, either by visiting `http://[url]:8421/responses` or clicking
the link on the dashboard (as mentioned in :ref:`exp-monitoring`).


Install Salmon
--------------

.. code-block:: shell

   $ git clone https://
   $ cd salmon
   $ conda env create -f salmon.yml
   $ conda activate salmon
   (salmon) $ pip install -e .

Generate embeddings
-------------------

This code will generate an embedding:

.. code-block:: python

   from salmon.triplets.offline import OfflineEmbedding

   df = pd.read_csv("responses.csv")
   X = df[["head", "winner", "loser"]].to_numpy()

   n = int(X.max() + 1)  # number of targets
   d = 2  # embed into 2 dimensions

   X_train, X_test = train_test_split(X, random_state=42, test_size=0.2)
   model = OfflineEmbedding(n=n, d=d)
   model.fit(X_train, X_test)

   model.embedding_  # embedding
   model.history_  # to view information on how well train/test performed

Some customization can be done with ``model.history_``; it may not be necessary
to train for 1,000,000 epochs. ``model.history_`` will include validation and
training scores, which might help limit the number of epochs.
