Developing algorithms
=====================

Install
-------

This process is meant for developers. To launch, first download the code.  It's
possible to download `a ZIP file of Salmon's source`_, or if Git is installed,
to run this command:

.. _a ZIP file of Salmon's source: https://github.com/stsievert/salmon/archive/refs/heads/master.zip

.. code:: shell

   $ git clone https://github.com/stsievert/salmon.git

Then, to launch a local version of Salmon you'll need `Docker Compose`_.
After that dependency is intalled, run the following code:

.. _install Docker: https://www.docker.com/products/docker-desktop
.. _install Git: https://git-scm.com/downloads

.. code:: shell

   $ cd salmon
   $ docker-compose build
   $ docker-compose up
   $ # visit http://localhost:8421/init or http://localhost:8421/docs

.. _Docker Compose: https://docs.docker.com/compose/install/

If you make changes to this code, run these commands:

.. code:: shell

	$ docker-compose stop
	$ docker-compose build
	$ docker-compose up

If you want to log into the Docker container, execute these commands:

.. code:: shell

   $ docker ps  # to get list of running conatiners
   CONTAINER ID   IMAGE             ... [more info]  ...  NAMES
   08b96fbcc4c3   salmon_server     ... [more info]  ...  salmon_server_1
   57cb3b7652d9   redislabs/rejson  ... [more info]  ...  salmon_redis_1
   $ docker exec -it 08b96fbcc4c3 /bin/bash
   (base) root@08b96fbcc4c3:/salmon# conda activate salmon
   (salmon) root@08b96fbcc4c3:/salmon#

.. note::

   This is an alternative way to install Salmon's dependencies. If you create a
   file in the Docker container in ``/salmon``, it will also be written to
   ``/path/to/salmon`` on your local machine.

If you run the command ``export SALMON_DEBUG=1``, the Salmon server will watch
for changes in the source and re-launch as necessary. This won't be perfect,
but it will reduce the number of times required to run ``docker-compose {stop,
build, up}``.

If you run the command ``export SALMON_NO_AUTH=1``, the Salmon server will
not require a username/password.

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

Use of ``get_queries`` is strongly recommended. Then Salmon's backend relies on
Dask, which allows for higher throughput (more concurrent users). ``get_query``
uses a single worker process, so it may get overloaded with a moderate number
of concurrent users.

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
