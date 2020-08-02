.. _adaptive-config:

Algorithm configuration
=======================

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

Let's start out with a simple ``init.yaml`` file, one suited for random
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

This will use :class:`~salmon.triplets.algs.TSTE`. If we want to customize to
include different keyword arguments, we need to look close at the arguments for
:class:`~salmon.triplets.algs.TSTE` [#]_. For example, this could be a
configuration:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}
     TSTE:
       alpha: 1.1

``alpha`` is a keyword argument to
:class:`~salmon.triplets.algs.adaptive.TSTE`.
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

.. [#] Most of the other algorithms like :class:`~salmon.triplets.algs.CKL`
       have very similar but slightly different configurations.
       :class:`~salmon.triplets.algs.CKL` and
       :class:`~salmon.triplets.algs.TSTE` have identical input parameters,
       except ``CKL``'s input ``mu`` and ``TSTE``'s ``alpha``.

