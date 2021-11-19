Developing algorithms
=====================

Basics
------

First, write an algorithm on your machine. The basic interface requires two
functions, one to get queries and one to process answers. Briefly, Salmon
expects two functions:

1. ``process_answers``, a function to process answers (which might involve
   updating the model).

2. A function to get queries. There are two choices for this:

    * ``get_query``, which returns a single query/score
    * ``get_queries``, which returns a list of queries and scores. These are
      saved in the database, and popped when a user requests a query.

For complete documentation, see :ref:`alg-api`. In short, your algorithm should
be a class that implement ``get_query`` and ``process_answers``.

After you have developed these functions, look at other algorithms in
``salmon/triplets/samplers`` (e.g, ``_adaptive_runners.py`` or ``_round_robin.py``)
to figure out inheritance details. In short, the following details are
important:

* **Inheriting from** :class:`~salmon.backend.alg.Sampler`, which enables Salmon
  to work with custom algorithms.
* **Accepting an** ``ident: str`` keyword argument in ``__init__`` **and
  passing that argument to** ``super().__init__``. (``ident`` is passed to all
  algorithms and is the unique identifier in the database).

I recommend the following when developing your algorithm. These aren't
necessary but are highly encouraged:

* **Have you algorithm be serializable:** ``pickle.loads(pickle.dumps(alg))``
  should work for your algorithm. Otherwise, your algorithm can't be restored
  on a new machine.
* **Ensure query searches are fast enough.** The user will be waiting if
  thousands of users come to Salmon and deplete all the searched queries.

It's not a strong requirement, but I would encourage both ``process_answers``
and ``get_queries`` to be quick and complete in about a second each.

Debugging
---------

Let's say you've integrated most of your algorithm into
:class:`~salmon.backend.sampler.Sampler`. Now, you'd like to make sure everything is
working properly.

This script will help:

.. code-block:: python

   from salmon.triplets.samplers import STE
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
   alg = STE(n=10, **params)  # or your custom alg
   for k in range(1000):
       query, score = alg.get_query()
       if query is None:
           queries, scores = alg.get_queries()
           h, a, b = queries[scores.argmax()]
           query = {"head": h, "left": a, "right": b, "score": scores.max()}

       answer = random_answer(query)
       alg.process_answers([answer])
