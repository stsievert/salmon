.. _adaptive-config:

.. _alg-config:

Algorithm configuration
=======================

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
     Random: {}
     Validation: {"n_queries": 10}

By default, ``samplers`` defaults to ``Random: {}``. We have to customize the ``samplers`` key use adaptive sampling algorithms:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     ARR: {}

When ``ARR`` is specified as a key for ``samplers``,
:class:`salmon.triplets.samplers.ARR` is used for the sampling method.
Customization is possible by passing different keyword arguments to
:class:`~salmon.triplets.samplers.ARR`. For example, this could be a
configuration:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     Random: {}
     ARR:
       module: "TSTE"

``module`` is a keyword argument to :class:`~salmon.triplets.samplers.ARR`, and
determines the noise model used for query scoring/embedding. This configuration
would compare two different instances of
:class:`~salmon.triplets.samplers.ARR`:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]

   samplers:
     Random: {}
     arr_tste:
       class: ARR
       module: "TSTE"
     arr_ckl:
       class: ARR
       module: "CKL"
       module__mu: 0.02

   sampling:
     probs: {"Random": 20, "arr_ckl": 40, "arr_tste": 40}

In this configuration, custom names are provided for two instances of
:class:`~salmon.triplets.samplers.ARR`. Both instances are sampled 40% of the
time, with the remaining 20% reserved for a test set with random queries.
