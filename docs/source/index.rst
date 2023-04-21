Welcome to Salmon's documentation!
==================================

Salmon is a tool to easily allow collection of "triplet queries." These queries
are relative similarity judgments of the form "is object :math:`a` or :math:`b`
closer to object :math:`h`?" An example is shown below with facial
similarities:

.. image:: imgs/query.png
   :width: 300px
   :align: center

These queries provide a relative similarity measure: a response indicates that
object :math:`a` is closer to object :math:`b` than object :math:`c` as
determined by humans. For example, these triplet queries have been used by
psychologists to determine what facial emotions human find similar:

.. image:: imgs/face-embedding.png
   :width: 500px
   :align: center

Only distance is relevant in this embedding, not the vertical/horizontal axes.
However, if you look closely, you can see two axes: positivity and intensity.

**Salmon provides efficient methods for collecting these triplet queries.**
Typically, generating the embeddings above requires far too many human
responses. Salmon provides the ability to generate the same embeddings with
fewer human responses – in our experiments, about 1,000 queries are required to
reach a particular quality level instead of about 3,000 queries. If you're
paying for each human response (say on Mechanical Turk), this means that
collecting responses will be reduced by a factor of 3 when compared with
naive methods of collecting triplet queries.

If you'd like to report bugs/issues, or improve Salmon please see `Salmon's
contribution guide`_. The list of dependicies and their licenses is available
at :ref:`deps`. Salmon is licensed under the BSD License. Details are at
`LICENSE.txt <https://github.com/stsievert/salmon/blob/master/LICENSE.txt>`_.

.. _Salmon's contribution guide: https://github.com/stsievert/salmon/blob/master/CONTRIBUTING.md

.. _users:

Users
=====

Salmon is currently being actively used by pyschologists from the University
of Wisconsin--Madison, and has seen some user from pyschologists at the
Louisiana State University and Canada's Western University.

If you use Salmon, please cite "`Efficiently Learning Relative Similarity
Embeddings with Crowdsourcing <https://doi.org/10.21105/joss.04517>`_", which
mentions this specific BibTex:

.. code-block:: none

   @article{Sievert2023,
     author = {Scott Sievert and Robert Nowak and Timothy Rogers},
     title = {Efficiently Learning Relative Similarity Embeddings with Crowdsourcing},
     journal = {Journal of Open Source Software}
     doi = {10.21105/joss.04517},
     url = {https://doi.org/10.21105/joss.04517},
     year = {2023},
     publisher = {The Open Journal},
     volume = {8},
     number = {84},
     pages = {4517},
   }


Salmon also has a `citation file <https://citation-file-format.github.io/>`_
file at `salmon/CITATION.cff
<https://github.com/stsievert/salmon/blob/master/CITATION.cff>`_.

.. raw:: html

   <a style="border-width:0" href="https://doi.org/10.21105/joss.04517">
     <img src="https://joss.theoj.org/papers/10.21105/joss.04517/status.svg" alt="DOI badge" >
   </a>
   <br>


.. toctree::
   :maxdepth: 2
   :caption: Usage

   installation
   getting-started
   init
   samplers
   frontend
   deploying
   monitoring
   offline
   faq
   api

.. toctree::
   :maxdepth: 2
   :caption: Benchmarks

   benchmarks/server
   benchmarks/active

.. toctree::
   :maxdepth: 1
   :caption: Algorithm Developers

   adaptive
   developers
   deps

Other sources of this documentation
-----------------------------------

This documentation is available at these locations:

* `https://docs.stsievert.com/salmon/ <https://docs.stsievert.com/salmon/>`_.
* On GitHub `as a raw PDF <https://github.com/stsievert/salmon/raw/gh-pages/salmon.pdf>`_  (`alternate link <https://github.com/stsievert/salmon/blob/gh-pages/salmon.pdf>`_).
* On GitHub as
  `a zipped HTML directory <https://github.com/stsievert/salmon/archive/refs/heads/gh-pages.zip>`_,
  which requires unzipping the directory then opening up ``index.html``.

Please `file an issue <https://github.com/stsievert/salmon/issues/new>`_ if you
can not access the documentation above.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



