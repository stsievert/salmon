Welcome to Salmon's documentation!
==================================

Salmon is a tool to easily allow collection of "triplet queries." These queries
are of the form "is object :math:`a` more similar to object :math:`b` or
:math:`b`?" An example is shown below with facial similarities:

.. image:: imgs/query.png
   :width: 300px
   :align: center

These queries are interesting because they provide some relative similarity
structure: a response might indicate that object :math:`a` is closer to object
:math:`b` than object :math:`c` as determined by humans and the instructions
they are given. For example, these triplet queries have been used by
psychologists to determine what facial emotions human find similar:

.. image:: imgs/face-embedding.png
   :width: 500px
   :align: center

Only distance is relevant in this embedding, not the vertical/horizontal axes.
However, if you look closely, you can see two axes: positivity and intensity.

Salmon provides efficient methods for collecting these triplet queries. For
example, Salmon can generate an accurate embedding from only 1,000 responses in
certain use cases. For the same use case, other approaches might require 2,000
responses. More detail is in the :ref:`benchmarks on active sampling
<experiments>`.

Users
=====

Salmon is currently being actively used by several  psychologists at the
University of Wisconsin--Madison, and has seen serious interest from the Air
Force Research Lab and a psychologist at Louisiana State University.

.. toctree::
   :maxdepth: 2
   :caption: Usage

   installation
   getting-started
   monitoring
   offline
   samplers
   api
   faq

.. toctree::
   :maxdepth: 2
   :caption: Benchmarks

   benchmarks/server
   benchmarks/active

.. toctree::
   :maxdepth: 2
   :caption: Algorithm Developers

   adaptive
   developers


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
