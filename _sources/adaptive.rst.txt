Adaptive algorithms
===================

.. warning::

   This interface is experimental and may change at any time.

There are many queries to ask about in triplet queries: with :math:`n` objects
there are :math:`\mathcal{O}(n^3)` questions that could be presented.

So what question should be asked? That's the task of an adaptive algorithm. The
API the must conform to below:


.. autosummary::

   backend.algs.Runner

Configuration
-------------


Adaptive algorithm API
----------------------
Runner
^^^^^^
.. currentmodule:: backend.algs

.. autoclass:: Runner
   :members:

RandomSampling
^^^^^^^^^^^^^^

.. autoclass:: RandomSampling

   .. automethod:: __init__

RoundRobin
^^^^^^^^^^

.. autoclass:: RoundRobin

   .. automethod:: __init__
