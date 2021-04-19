FAQ
===

How many responses will be needed?
----------------------------------

Depends on your targets, and how humans respond. Let's say you have :math:`n`
targets that are being embedded into :math:`d` dimensions. At most, we can
provide bounds on how many responses you'll need:

* **Lower bound:** at least :math:`nd\log_2(n)` responses are needed for a
  perfect embedding (aka sorting :math:`n` items in :math:`d`
  dimensions independently). Triplet embeddings have been shown in obey this
  bound. [1]_
* **Upper bound:** if random responses are collected, you'll probably be fine
  with :math:`20 nd \log_2(n)` responses. You might be fine with :math:`10 nd
  \log_2(n)`. [2]_

For how ever many responses random sampling requires, our experiments indicate
about a factor of 2 or 3 less responses will be required.

.. [1] "Low-dimensional embedding using adaptively selected ordinal data."
   Jamieson and Nowak. 2011. Allerton Conference on Communication, Control, and
   Computing. https://homes.cs.washington.edu/~jamieson/resources/activeMDS.pdf
.. [2] "Finite sample prediction and recovery bounds for ordinal embedding."
   Jain, Jamieson and Nowak. 2016. NeurIPS.
   https://nowak.ece.wisc.edu/ordinal_embedding.pdf

What adaptive algorithms are recommended?
-----------------------------------------

We recommend :class:`~salmon.triplets.samplers.ARR` for triplet scenarios.
Most of our experiments were run  with that algorithm.


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

Look at port 8787 if you want more information on how jobs are scheduled. This
will require some port forwarding to your own machine:

.. code:: shell

   ssh -i key.pem -L 7787:localhost:8787 ubuntu@34.222.199.114
   # visit http://localhost:7787 in the browser to see Salmon's Dask dashboard
