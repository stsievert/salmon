.. _adaptive-config:

.. _alg-config:

Sampler configuration
=====================

There are many queries to ask about in triplet embedding tasks. Most of these
queries aren't useful; chances are most queries will have obvious answers and
won't improve the embedding much.

Choosing the most useful queries to improve the embedding is the task of
"active machine learning" aka "adaptive sampling algorithms." These algorithms
use all previous responses collected to determine the next query that will help
improve the embedding the most.

If quality embeddings are desired, the benchmarks at ":ref:`experiments`" are
likely of interest, as are the FAQs on ":ref:`random_vs_active`" and
":ref:`adaptiveconfig`" However, quality embeddings may not always be of
interest: sometimes, the goal is not to generate a good embedding, but rather
to see how well the crowd agrees with each other, or to make sure participants
don't influence each other (and each response is independent of other
responses). Here's a rule of thumb:

.. note::

   **Want an unbiased estimate of what the crowd thinks?** Don't specify
   ``samplers``, or use the default ``Random: {}``, which will rely on
   :class:`~salmon.triplets.samplers.Random`

   **Want to generate a better embedding? Worried about the cost of
   collecting responses?** Use ``ARR: {}``, which will rely on
   :class:`~salmon.triplets.samplers.ARR`.

   **Want to measure how well the crowd agrees with one another?** Use
   ``Validation: {}``, which will rely on
   :class:`~salmon.triplets.samplers.Validation`,

Now, let's go over how to configure those classes and an example.

File structure
--------------

Part of a ``init.yaml`` configuration file might look like this:

.. code-block:: yaml

   # file: init.yaml
   samplers:
     ARR: {random_state: 42}
     Random: {}
   sampling:
     probs: {"ARR": 85, "Random": 15}

This will create the a versions of :class:`~salmon.triplets.samplers.ARR` with
``random_state=42`` would be created alongside the default version of
:class:`~salmon.triplets.samplers.Random`. When a query is generated, it will be
generated from ``ARR`` 85% of the time and from ``Random`` the rest of the
time. Generally, the keys in ``samplers`` and ``sampling`` follow these general
rules:

* ``samplers``: controls how one specific sampler behaves (i.e., class
  initialization). The class is specified each key, and any arguments are
  passed to the class instance.
* ``sampling``: controls samplers interact. For example:

  * the ``probs`` key controls how frequently each class instance in
    ``samplers`` is used
  * the ``common`` key controls sending initialization arguments to `every`
    class instances.
  * the ``samplers_per_user`` key controls how many samplers are seen by any
    one user who visits Salmon.

A good default configuration is mentioned in the FAQ ":ref:`adaptiveconfig`"
The defaults and complete details are in
:class:`~salmon.triplets.manager.Config`.

Multiple classes of the same name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If two classes with different purposes want to be used, the key ``class`` is
used:

.. code-block:: yaml

   # file: init.yaml
   samplers:
     testing:
       class: Random
     training:
       class: Random

This will generate queries from these two samplers with equal probability:

.. code-block:: python

   from salmon.triplets.samplers import Random
   Random()
   Random()

Initialization arguments
^^^^^^^^^^^^^^^^^^^^^^^^

Arguments inside each key are passed to the sampler. For example,

.. code-block:: yaml

   # file: init.yaml
   samplers:
     ARR:
       random_state: 42
       module: CKL
       d: 3
       scorer: "uncertainty"

would create an instance of :class:`~salmon.triplets.samplers.ARR`:

.. code-block:: python

   from salmon.triplets.samplers import ARR
   ARR(random_state=42, module="CKL", d=3, scorer="uncertainty")

Note that the argument are documented in
:class:`~salmon.triplets.samplers.ARR`. Some argument are arguments that
:class:`~salmon.triplets.samplers.ARR` directly uses (like ``module``), and
other are passed to :class:`~salmon.triplets.samplers.Adaptive` as mentioned in
the docstring of :class:`~salmon.triplets.samplers.ARR`.

If you have multiple arguments for *every* class, you can specify that with the
``common`` key:

.. code-block:: yaml

   # file: init.yaml
   samplers:
     arr_tste:
       module: TSTE
     arr_ckl:
       module: CKL
   sampling:
     common:
       d: 3
       random_state: 42

This would initialize these classes:

.. code-block:: python

   from salmon.triplets.samplers import ARR
   ARR(module="TSTE", d=3, random_state=42)
   ARR(module="CKL",  d=3, random_state=42)


Example
-------

Let's start out with a simple ``init.yaml`` file, one suited for random
sampling.

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     Random: {}
     Validation: {"n_queries": 10}

By default, ``samplers`` defaults to ``Random: {}``. We have to customize the ``samplers`` key use adaptive sampling algorithms:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     ARR: {}
     Random: {}
     Validation: {"n_queries": 10}
   sampling:
     probs: {"ARR": 70, "Random": 20, "Validation": 10}


When ``ARR`` is specified as a key for ``samplers``,
:class:`salmon.triplets.samplers.ARR` is used for the sampling method.
Customization is possible by passing different keyword arguments to
:class:`~salmon.triplets.samplers.ARR`. For example, this could be a
configuration:

.. code-block:: yaml

   targets: ["obj1", "obj2", "foo", "bar", "foobar!"]
   samplers:
     Random: {}
     ARR:
       module: "TSTE"
