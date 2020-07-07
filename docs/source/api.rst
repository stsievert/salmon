Algorithm API
=============

.. warning::

   These APIs are experimental and may change at any time.

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

   salmon.triplets.algs.TSTE
   salmon.triplets.algs.STE
   salmon.triplets.algs.CKL
   salmon.triplets.algs.GNMDS
