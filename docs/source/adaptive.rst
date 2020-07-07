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

Developing adaptive algorithms
------------------------------

The API the must conform to below:


.. autosummary::

   salmon.backend.alg.Runner

This API balances the fundamentally serial nature of adaptive algorithms with
the parallel context of web servers.

Typically, an adaptive algorithm looks like the following:

.. code-block:: python

   model = Model(...)
   while True:
       query = get_one_query()
       ans = get_human_answer(query)
       model.fit(ans)

However, web servers are different. They typically look something like the
following:

.. code-block:: python

   @app.get("/query")
   async def query():
       return get_one_query()

   @app.post("/answer")
   async def process_answer(answer):
       db.push(answer)

The :class:`~salmon.backend.alg.Runner` API balances the two. It runs both sets
of code in parallel processes. That means one can not block the other. However,
this also means that the adaptive algorithm has to produce queries quickly
enough. Enough queries are produced because the scoring is rather fast [#]_ and
every query is scored.

.. [#] Fast enough to search 10,000 queries in 50ms with :math:`n = 85` objects.
