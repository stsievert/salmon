.. _adaptive-config:

.. _alg-config:

Algorithm configuration
=======================

.. warning::

   The API for these algorithms is (currently) unstable.

There are many queries to ask about in triplet embedding tasks. Most of these
queries aren't useful; chances are most queries will have obvious answers and
won't improve the embedding much.

Choosing the most useful queries to improve the embedding is the task of
"active machine learning" aka "adaptive sampling algorithms." These algorithms
use all previous responses collected to determine the next query that will help
improve the embedding the most.

Let's start out with a simple ``init.yaml`` file, one suited for random
sampling.

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}

By default, ``samplers`` defaults to ``RandomSampling: {}``. We have to customize the ``samplers`` key use adaptive sampling algorithms:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     ARR: {}

This will use :class:`~salmon.triplets.samplers.ARR`. If we want to customize to
include different keyword arguments, we need to look close at the arguments for
:class:`~salmon.triplets.samplers.ARR` [#]_. For example, this could be a
configuration:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     RandomSampling: {}
     ARR:
       module: "TSTE"
       optimizer__batch_size: 1024

``module`` is a keyword argument to
:class:`~salmon.triplets.samplers.ARR`.
If we want to use two alternate configs for ARR:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]

   samplers:
     RandomSampling: {}
     arr_ckl:
       class: ARR
       module: "CKL"
     arr_tste:
       class: ARR
       module: "TSTE"

   sampling:
     probs: {"RandomSampling": 20, "arr_ckl": 40, "arr_tste": 40}

This would test out different optimization methods underlying the embedding.

.. [#] Most of the other algorithms like :class:`~salmon.triplets.samplers.CKL`
       have very similar but slightly different configurations.
       :class:`~salmon.triplets.samplers.CKL` and
       :class:`~salmon.triplets.samplers.TSTE` have identical input parameters,
       except ``CKL``'s input ``mu`` and ``TSTE``'s ``alpha``.
