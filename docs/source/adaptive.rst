
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

.. _adaptive-config:

Algorithm Configuration
-----------------------

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
       q = model.best_query()
       ans = get_human_answer(q)
       model.fit(ans)

However, web servers are different. They typically look something like the
following:

.. code-block:: python

   @app.get("/query")
   async def query():
       return db.pop("queries")

   @app.post("/answer")
   async def process_answer(answer):
       db.push(answer)

The :class:`~salmon.backend.alg.Runner` API balances the two and runs the code
to `receive answers` and `process answers` in separate processes.
`Processing the received answers` is an optimization that needs to be performed
quickly because ``model.best_query`` depends on the optimization.

Essentially, the following code is run in addition to the web server code
above:

.. code-block:: python

   db = Database(...)

   def run_alg():
       model = Model(...)
       while True:
           queries = [model.score(random_query()) for _ in range(10_000)]
           db.push("queries", queries)
           answers = db.pop_all("answers")
           model.partial_fit(answers)

This means the web server can scale efficiently because the backend
optimization doesn't block the frontend query serving. However, that also means
the adaptive algorithm needs to post queries quickly so users aren't waiting.
Of course, the computation required to perform the embedding needs to happen
quickly too (otherwise adaptive algorithms are meaningless).

Luckily, Salmon should scale sufficiently well for typical use cases (e.g,
Mechnical Turk with about :math:`n \approx 100` targets). The query search is
fast enough to search 10,000 queries in 50ms with :math:`n = 85` targets.
