Adaptive algorithms
===================

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
