Adaptive algorithms
===================

.. warning::

   These adaptive algorithms are (currently) experimental and may change at any
   time. Do not use these adaptive algorithms in deployment.

There are many queries to ask about in triplet embedding tasks. Most of these
queries aren't useful; chances are most queries will have obvious answers and
won't improve the embedding much.

Choosing the most useful queries to improve the embedding is the task of
"active machine learning" aka "adaptive sampling algorithms." These algorithms
use all previous responses collected to determine the next query that will help
improve the embedding the most.

Below, the following will be detailed:

1. How to specify adaptive algorithms, and how to configure them.
2. How to write a new adaptive algorithms.

Configuration
-------------

Let's start out with a simple ``exp.yaml`` file, one suited for random
sampling:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}

By defualt, ``samplers`` defaults to ``RandomSampling: {}``. We have to customize the ``samplers`` key use adaptive sampling algorithms:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     TSTE: {}

This will use :class:`~salmon.triplets.algs.adaptive.TSTE`. If we want to
customize to include different keyword arguments, we need to look close at the
arguments for :class:`~salmon.triplets.algs.adaptive.Embedding` or it's
children. For example, this could be a configuration:

:class:`~salmon.triplets.algs.RoundRobin`
:class:`~salmon.triplets.algs.CKL`

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}
     TSTE:
       module__alpha: 1.1

If we want to use two alternate configs for TSTE:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}
     TSTE:
       optimizer: Embedding
       optimizer__lr: 0.1
     tste1:
       module: TSTE
       optimizer: PadaDampG
       optimizer__lr: 0.1
     tste2:
       module: TSTE
       optimizer: GeoDamp
       optimizer__lr: 0.1

This would test out different optimization methods underlying the embedding.


Developing adaptive algorithms
------------------------------

The API the must conform to below:


.. autosummary::

   salmon.backend.alg.Runner
