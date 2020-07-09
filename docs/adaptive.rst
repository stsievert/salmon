Adaptive algorithms
===================

.. warning::

   These adaptive algorithms are (currently) experimental and may change at any
   time. Do not use these adaptive algorithms in deployment.

There are many queries to ask about in triplet queries: with :math:`n` objects
there are :math:`\mathcal{O}(n^3)` questions that could be presented.

So what question should be asked? That's the task of an adaptive algorithm. The
API the must conform to below:


.. autosummary::

   salmon.backend.alg.Runner

Configuration
-------------

Every adaptive algorithm takes different parameters. How should the parameters
be configured in the YAML file provided on upload?


