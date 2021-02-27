.. _alg-api:

Algorithm API
=============

.. warning::

   These APIs are unstable.

All triplet embedding algorithms must conform to this API:

.. autosummary::
   :toctree: generated/
   :template: class.rst

   salmon.backend.alg.Runner

This class enables running a triplet embedding algorithm on Salmon: it provides
convenient hooks to the database like ``get_queries`` and ``post_answers`` if
you want to customize the running of the algorithm. By default, the algorithm
uses ``Runner.run`` to run the algorithm.

Every class below inherits from :class:`~salmon.backend.alg.Runner`.


Passive Algorithms
------------------

.. currentmodule:: salmon

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.algs.RandomSampling
   salmon.triplets.algs.RoundRobin

Active Algorithms
-----------------

.. currentmodule:: salmon

.. autosummary::
   :toctree: generated/
   :template: only-init.rst

   salmon.triplets.algs.RR
   salmon.triplets.algs.TSTE
   salmon.triplets.algs.STE
   salmon.triplets.algs.CKL
   salmon.triplets.algs.GNMDS

These adaptive algorithms are all the same except for the underlying noise
model, with the exception of :class:`~salmon.triplets.algs.RR`.
:class:`~salmon.triplets.algs.RR` introduces some randomness by fixing the head
and adding the top ``5 * n`` triplets to the database. This is useful because
the information gain measure used by all of these algorithms (by default) is a
rule-of-thumb.

.. note::

   Use of :class:`~salmon.triplets.algs.RR` is recommended as it performs well
   in :ref:`the experiments we have run <experiments>`.

Interface
---------

These algorithms all implement this interface:

.. code-block:: python

   import numpy as np
   from salmon.backend import Runner
   from typing import Union, Tuple, Dict

   class MyAlg(Runner):
       def __init__(self, ..., ident=""):
           ...
           super().__init__(ident=ident)

       def get_query(self) -> Tuple[Optional[Dict[str, int]], float]:
           """
           Get a single query for the user.

           Returns
           -------
           query : Dict[str, int], None
               The query for the user. Must contain keys `head`, `left` and
               `right` for triplets.

               If this function returns a None query, the default loop will pull
               the highest scoring query from ``get_queries`` (through the
               database; not directly).

           score : float
               The query score. Piped to the user, not used directly.

           """
           return {"head": 0, "left": 1, "right": 2}, 0.0

       def process_answers(self, answers):
           """
           Process the answers, or update the model.

           Parameters
           ----------
           answers : list of answers.
               Each answer is a dictionary with the same keys as the query
               returned by `get_query`. In addition, at has keys for `winner`.
           """

       def get_queries(self):
           """
           Score many queries.

           Returns
           -------
           queries : array-like, List[Tuple[int, int, int]]
               Queries to ask about. Queries take form `[head, left, right]` and
               are expected to be integers.

               Serialized in the database by `Runner.serialize_queries`, and
               de-serialized by `manager.deserialize_queries`.

           scores : array-like (floats)
               The scores of the queries.

           """
           queries, scores = self.score_queries()
           return queries, scores
