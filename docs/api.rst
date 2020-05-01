Algorithm API
=============

.. warning::

   These APIs are experimental and may change at any time.

Briefly, the algorithms mentioned in this section are:

.. autosummary::

   salmon.triplets.algs.RandomSampling
   salmon.triplets.algs.RoundRobin


Base API
--------
All adaptive algorithms must conform to this API:

.. autoclass:: salmon.backend.alg.Runner
   :members:


Specific algorithms
-------------------
Here are the details on the specific algorithms:

.. autoclass:: salmon.triplets.algs.RandomSampling

   .. automethod:: __init__

.. autoclass:: salmon.triplets.algs.RoundRobin

   .. automethod:: __init__
