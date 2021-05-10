FAQ
===

.. _faq-n_responses:

How many responses will be needed?
----------------------------------

Depends on the targets used, and how humans respond. Let's say there are
:math:`n` targets that are being embedded into :math:`d` dimensions. At most,
we can provide bounds on how many responses you'll need:

* **Lower bound:** at least :math:`nd\log_2(n)` responses are needed for a
  perfect embedding (aka sorting :math:`n` items in :math:`d` dimensions
  independently). Triplet embeddings have been shown in obey this bound. [1]_
* **Upper bound:** if random responses are collected, a high quality embedding
  will likely be generated with :math:`20 nd \log_2(n)` responses, possibly
  :math:`10 nd \log_2(n)`. [2]_

See the :ref:`benchmarks on active sampling <experiments>` for more detail and
specific numbers.

What adaptive algorithms are recommended?
-----------------------------------------

We recommend :class:`~salmon.triplets.samplers.ARR` for triplet scenarios.  See
the :ref:`benchmarks on active sampling <experiments>` for an example
configuration.

Can I choose a different machine?
---------------------------------

All of our experiments are run with ``t3.xlarge`` instances. If you want to
choose a different machine, ensure that is has the following:

* At least 4GB of RAM
* At least 3 CPU cores.

These are required because Salmon requires 3.2GB of memory and Dask has three
tasks per adaptive algorithm: posting queries, searching queries, model
updating. Generally, the number of cores should be ``3 * n_algs``. This isn't a
strict guideline; only 2 out of the 3 tasks take significant amounts of time.
Using ``2 * n_algs`` will work at a small performance hit; we recommend at
least 4 cores for two algorithms.

How do I see the Dask dashboard?
--------------------------------

Look at port 8787 if you want more information on how jobs are scheduled. If on
EC2, this will require some port forwarding to your own machine:

.. code:: shell

   ssh -i key.pem -L 7787:localhost:8787 ubuntu@34.222.199.114
   # visit http://localhost:7787 in the browser to see Salmon's Dask dashboard

If desired, it is possible to open port 8787 on the Amazon EC2 machine. If that
action is taken, it is recommended to only allow a specific IP to view that
port.

.. [1] "Low-dimensional embedding using adaptively selected ordinal data."
   Jamieson and Nowak. 2011. Allerton Conference on Communication, Control, and
   Computing. https://homes.cs.washington.edu/~jamieson/resources/activeMDS.pdf
.. [2] "Finite sample prediction and recovery bounds for ordinal embedding."
   Jain, Jamieson and Nowak. 2016. NeurIPS.
   https://nowak.ece.wisc.edu/ordinal_embedding.pdf
