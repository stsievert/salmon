.. _faq:

FAQ
===

Also relevant is the :ref:`troubleshooting`, which goes over some (blocking)
difficulties while launching.

.. note::

   Please include the version in any bug reports or feature requests.  The
   version number should look something like ``v0.4.1``. It can be found at
   ``http://[url]:8421/docs`` or in the downloaded experiment file (found at
   ``http://[url]:8421/download`` which has a filename like
   ``exp-2021-05-20T07:31-salmon-v0.4.1.rdb``).

.. _random_vs_active:

When should I use random/active sampling?
-----------------------------------------

Rule of thumb:

* Use random sampling for simple problems when not many responses are required
  (small number of targets and clean responses).
* Use active sampling for anything more complicated (large number of targets or
  noisy responses) when the crowdsourcing budget and/or embedding quality are
  relevant.

Specifics are :ref:`faq-n_responses` and :ref:`adaptiveconfig`. Random sampling
can produce good embeddings, but will require about 3× the number of responses
that active sampling requires.

By default, Salmon will produce random embeddings. This is the simplest
sampler, and doesn't require any user configuration. Tips on how to use active
samplers are in :ref:`adaptiveconfig`.

.. _faq-n_responses:

How many responses will be needed?
----------------------------------

Depends on the targets used, and how humans respond. Let's say there are
:math:`n` targets that are being embedded into :math:`d` dimensions. At most,
we can provide bounds on how many responses you'll need:

* **Lower bound:** at least :math:`nd\log_2(n)` responses are needed for a
  `perfect` embedding with noiseless responses. Active triplet algorithms
  require :math:`\Omega(nd\log_2(n))` responses (so a constant number of
  responses more/less). [1]_
* **Upper bound:** if random responses are collected, a high quality embedding
  will likely be generated with :math:`O(nd\log_2(n))` responses, likely
  :math:`20 nd \log_2(n)` responses (or possibly :math:`10 nd \log_2(n)`). [2]_


This suggests that the number of responses required when :math:`n` and
:math:`d` are changed scaled like :math:`nd\log_2(n)`.  i.e, if an embedding
below requires 5,000 responses for :math:`n=30`, scaling to :math:`n=40` with
:math:`d=1` would likely require about :math:`3600 \approx 5000\frac{40 \cdot 1
\cdot \log_2(40)}{30\cdot 2 \cdot \log_2(30)}` responses for the same dataset.

See the :ref:`benchmarks on active sampling <experiments>` for some
benchmarks/landmarks on the specific number of responses required for a
particular dataset. **If you think your dataset will require too many
responses,** see :ref:`our recommendations on active samplers
<adaptiveconfig>`. Active samplers might be able to generate better embeddings
with a fixed number of responses.

.. _adaptiveconfig:

What active samplers are recommended?
-------------------------------------

Use of :class:`~salmon.triplets.samplers.ARR` is most recommended.  See the
:ref:`benchmarks on active sampling <experiments>` for an example configuration
and the number of responses required for that usage.  The defaults of
:class:`~salmon.triplets.samplers.ARR` have been explored pretty throughly. In
the :ref:`benchmarks on active sampling <experiments>`, we used the default
parameters for :class:`~salmon.triplets.samplers.ARR` after exploring the
possible values.

Monitoring performance is difficult with active/adaptive algorithm; random
sampling is a lot better. Typically, between 10% and 20% of the sampling is
used to monitor and report performance. That means I'd recommend this partial
configuration:

.. code-block:: yaml

   samplers:
     ARR: {}
     Random: {}
   sampling:
     probs: {"ARR": 85, "Random": 15}

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

.. _specificquestion:

How do I ask specific questions?
--------------------------------

It's possible to configure what queries get shown to the crowdsourcing user
with two methods:

1. By using :class:`~salmon.triplets.samplers.Validation`.  You can specify a
   list of queries, or generate ``n_queries`` random queries. See
   :ref:`alg-config` and the :ref:`valconfig` section.
2. By specifying the ``query`` key in
   :class:`~salmon.triplets.manager.Sampling`'s ``detail`` field.  This allows
   showing users specific queries at specific times.  e.g., "for the first
   query the user sees, show them a query with [these objects]."
    * Example: :ref:`valdetail`
    * Example: the documentation for
      :class:`~salmon.triplets.manager.Sampling`.

.. _whichsampler:

How do I specify when samplers are used?
----------------------------------------

Controlling when or how often samplers get used is possible with two methods:

1. By setting the ``probs`` key in :class:`~salmon.triplets.manager.Sampling`.
   If the YAML specifies ``sampling.probs: {"ARR": 80, "Random": 20}``, the
   ``Random`` sampler will be used 20% of the time.
2. By setting the ``sampler`` field in
   :class:`~salmon.triplets.manager.Sampling`'s ``detail`` field. This will
   ensure that the query is generated by a specific sampler (or which sampler
   will receive the answer if the query is pre-specified in your ``init.yaml``
   per ":ref:`specificquestion`").

When ``sampling.probs`` is specified in your ``init.yaml``, Salmon serves a
query to a user with a certain *probability.* This can pose difficulties if you
want to ask *exactly* :math:`N` questions to each crowdsourcing participant.
Specifying ``sampling.details`` in your ``init.yaml`` will work around this and
allow configuring the details of particular queries.

How do I ask every crowdsourcing user exactly the same questions?
-----------------------------------------------------------------

By specifying both the ``sampler`` key and the ``query`` key in
:class:`~salmon.triplets.manager.Sampling`'s ``detail`` field. The answers to
the questions ":ref:`whichsampler`" and ":ref:`specificquestion`" are relevant.

An example is in ":ref:`valdetail`", delegated to the :ref:`alg-config` page
because the target indexing in ":ref:`valconfig`" is relevant.

How do I see the Dask dashboard?
--------------------------------

Look at port 8787 if you want more information on how jobs are scheduled. If on
EC2, this will require some port forwarding to your own machine:

.. code:: shell

   ssh -i key.pem -L 7787:localhost:8787 ubuntu@[EC2 public DNS or IP]
   # visit http://localhost:7787 in the browser to see Salmon's Dask dashboard

If desired, it is possible to open port 8787 on the Amazon EC2 machine. If that
action is taken, it is recommended to only allow a specific IP to view that
port.

How do I customize the participant unique identifier aka "puid"?
----------------------------------------------------------------

Visiting ``http://[url]:8421/?puid=foobar`` will set that the participant UID
to be ``foobar``.

How do I use HTTPS with Salmon?
-------------------------------

HTTP is how web servers communicate; HTTPS protects that communication from
third parties.

Some crowdsourcing services require HTTPS. There are to ways to provide these
crowdsourcing services an HTTPS URL:

1. Redirect to Salmon from an HTTPS page.
2. Set up a `TLS termination proxy`_.

Option (1) is a lot easier because various hosting services support HTTPS
(e.g., `GitHub Pages`_ and `GitLab Pages`_ support HTTPS for custom domains).
Hosting a `redirect HTML page`_ at one of these services with HTTPS will likely
satisfy any requirements you may have.

Option (2) is more complex. A good overview is at FastAPI's page "`About
HTTPS`_," available at https://fastapi.tiangolo.com/deployment/https/. This
process is beyond scope for this project. [#f]_

.. _mkcert: https://github.com/FiloSottile/mkcert
.. _About HTTPS: https://fastapi.tiangolo.com/deployment/https/
.. _redirect HTML page: https://www.w3docs.com/snippets/html/how-to-redirect-a-web-page-in-html.html
.. _GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https
.. _GitLab Pages: https://docs.gitlab.com/ee/user/project/pages/custom_domains_ssl_tls_certification/
.. _TLS termination proxy: https://en.wikipedia.org/wiki/TLS_termination_proxy

.. [1] "Low-dimensional embedding using adaptively selected ordinal data."
   Jamieson and Nowak. 2011. Allerton Conference on Communication, Control, and
   Computing. https://homes.cs.washington.edu/~jamieson/resources/activeMDS.pdf
.. [2] "Finite sample prediction and recovery bounds for ordinal embedding."
   Jain, Jamieson and Nowak. 2016. NeurIPS.
   https://nowak.ece.wisc.edu/ordinal_embedding.pdf

.. [#f] though the package `mkcert`_ might help.

The Docker machines aren't launching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Are you using the command ``docker-compose up`` to launch Salmon? The command
``docker build .`` doesn't work.

Salmon requires a Redis docker machine and certain directories/ports being
available. Technically, it's possible to build all the Docker machines
yourself (but it's not feasible).
