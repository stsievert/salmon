Developing algorithms
=====================

Basics
------

First, write an algorithm on your machine. It should define the following
functions:

* ``get_queries() -> Tuple[Query, List[float]]``.
* ``process_answers[List[Answers]]``.

Details can be found in :class:`~salmon.backend.alg.Runner`. Your algorithm should
be a class, and it can store internal state.

After you have developed these functions, look at other algorithms in
`salmon/triplets/algs` (e.g, ``_adaptive_runners.py`` or ``_round_robin.py``)
to figure out inheritance details. In short, the following details are
important:

* Inheriting from :class:`~salmon.backend.alg.Runner` is important; that's what
  enables Salmon to work with custom algorithms. This class requires
  implementations of ``get_query``/``get_queries`` and ``process_answers``.
* Accepting an ``ident: str`` keyword argument in ``__init__`` and passing that
  argument to :class:`~salmon.backend.alg.Runner`.

I recommend the following when developing your algorithm. These aren't
necessary but are highly encouraged:

* **Have you algorithm be serializable:** ``pickle.loads(pickle.dumps(alg))``
  should work for your algorithm.
* **Ensure query searches are fast enough.** The user will be waiting if
  thousands of users come to Salmon and deplete all the searched queries.

It's not a strong requirement, but I would encourage both ``process_answers``
and ``get_queries`` to be quick and complete in about a second each.

Debugging
---------

Let's say you've integrated most of your algorithm into
:class:`~salmon.backend.alg.Runner`. Now, you'd like to make sure everything is
working properly.

This script will help:

.. code-block:: python

   from salmon.triplets.algs import STE
   from copy import copy
   import random

   def random_answer(q):
       ans = copy(q)
       winner = random.choice(["left", "right"])
       ans["winner"] = q[winner]
       return ans

   params = {
       "optimizer__lr": 0.1,
       "optimizer__momentum": 0.75,
   }
   alg = STE(n=10, **params)
   for k in range(1000):
       query, score = alg.get_query()
       if query is None:
           queries, scores = alg.get_queries()
           h, a, b = queries[scores.argmax()]
           query = {"head": h, "left": a, "right": b, "score": scores.max()}

       answer = random_answer(query)
       alg.process_answers([answer])
