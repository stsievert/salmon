.. _alg-api:

.. _api:

API
===

Offline embeddings
------------------

This class can be used to create embeddings from a set of downloaded responses
from Salmon:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   salmon.triplets.offline.OfflineEmbedding

Samplers
--------

These classes are used to collect responses with Salmon. They can be configured
using ``init.yaml`` as mentioned in :ref:`alg-config`. They all conform to the
following API:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   salmon.backend.sampler.Runner

This class enables running a triplet embedding algorithm on Salmon: it provides
convenient hooks to the database like ``get_queries`` and ``post_answers`` if
you want to customize the running of the algorithm. By default, the algorithm
uses ``Runner.run`` to run the algorithm.

Every class below inherits from :class:`~salmon.backend.sampler.Runner`.


Passive Algorithms
^^^^^^^^^^^^^^^^^^

.. currentmodule:: salmon

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.samplers.RandomSampling
   salmon.triplets.samplers.RoundRobin
   salmon.triplets.samplers.Validation

Active Algorithms
^^^^^^^^^^^^^^^^^

Every active algorithm inherits from one class:

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.samplers.Adaptive

The class :class:`~salmon.triplets.samplers.Adaptive` runs the adaptive algorithm
and depends on :class:`~salmon.triplets.samplers.adaptive.Embedding` for
optimization:

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.samplers.adaptive.Embedding

To customize the optimization, all extra keyword arguments are passed to the
optimizer.

Then, all of these classes inherit from
:class:`~salmon.triplets.samplers.Adaptive`:

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.samplers.ARR
   salmon.triplets.samplers.TSTE
   salmon.triplets.samplers.SOE
   salmon.triplets.samplers.STE
   salmon.triplets.samplers.CKL
   salmon.triplets.samplers.GNMDS

We have tested out the top three algorithms---ARR, TSTE and SOE---in our
experiments. We use :class:`~salmon.triplets.samplers.ARR` for our adaptive sampling
(which defaults to the noise model in :class:`~salmon.triplets.samplers.TSTE`) and
use :class:`~salmon.triplets.samplers.SOE` for the offline embeddings.

These adaptive algorithms are all the same except for the underlying noise
model, with the exception of :class:`~salmon.triplets.samplers.ARR`.
:class:`~salmon.triplets.samplers.ARR` introduces some randomness by fixing the head
and adding the top ``1 * n`` triplets to the database. This is useful because
the information gain measure used by all of these algorithms (by default) is a
rule-of-thumb.

.. note::

   Use of :class:`~salmon.triplets.samplers.ARR` is recommended as it performs well
   in :ref:`the experiments we have run <experiments>`.
