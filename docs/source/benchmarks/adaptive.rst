Adaptive algorithms
===================

Adaptive algorithms decide which questions to ask about, instead of asking
about a random question like random sampling. This can mean that higher
accuracies are reached sooner, or that less human responses are required to
reach a particular accuracy.

Synthetic simulation
--------------------

Let's compare adaptive sampling and random sampling. Specifically, let's use
Salmon like an experimentalist would:

1. Launch Salmon with the "alien eggs" dataset (with :math:`n=50` objects and
   using :math:`d=2` dimensions).
2. Simulate human users (6 users with mean response time of 1s).
3. Download the human responses from Salmon
4. Generate the embedding offline.

Let's run this process for adaptive and random sampling. When we do that, this
is the graph that's produced:

.. image:: imgs/synth-eg-acc.png
   :width: 600px
   :align: center

These are synthetic results, though they use a human noise model. These
experiments provide evidence that Salmon works well with adaptive sampling.

This measure provide evidence to support the hypothesis that Salmon has better
performance than NEXT for adaptive triplet embeddings. For reference, in NEXT's
introduction paper, the authors found "no evidence for gains from adaptive
sampling" for the triplet embedding problem [2]_.

.. [1] "Active Perceptual Similarity Modeling with Auxiliary Information" by E.
       Heim, M. Berger, and L. Seversky, and M. Hauskrecht. 2015.
       https://arxiv.org/pdf/1511.02254.pdf

.. [2] "NEXT: A System for Real-World Development, Evaluation, and Application
       of Active Learning" by K. Jamieson, L. Jain, C. Fernandez, N. Glattard
       and R. Nowak. 2017.
       http://papers.nips.cc/paper/5868-next-a-system-for-real-world-development-evaluation-and-application-of-active-learning.pdf


Search efficacy
---------------

Adaptive algorithms are more adaptive if they search more queries. Random sampling
can be thought of as an adaptive algorithm that only searches over one possible
query. An algorithm that searches over 50,000 queries is more adaptive than a
algorithm that can only search 50 queries.

How much do these searches matter? Let's run another experiment with this setup:

* Dataset: strange fruit dataset. The response model will be determined from human
  responses. There will be :math:`n=200` objects and that will be embedded into :math:`d=2`
  dimensions.
* Let's measure **search efficacy.** To aid this, let's say model updates run instantly.
  That means we'll run offline using essentially this code:

.. code-block:: python

   responses_per_search = 10
   n_search = 10
   alg = TSTE(n=n, d=d, ...)

   for k in itertools.count():
       queries, scores = alg.score_queries(num=n_search * responses_per_search)
       queries = _get_top_N_queries(queries, scores, N=responses_per_search)
       answers = [_get_answer(query) for query in queries]

       alg.partial_fit(answers)  # performs 1 pass over all answers received thus far

With that, we see this performance:

.. image:: imgs/search-efficacy.png
   :width: 600px
   :align: center

If you only have the budget for 4,000 queries the most complete search will reach about 82% accuracy. The least complete search will only reach about 60% accuracy.

If you want to reach 80% accuracy, the most complete searches will require about 3,800 queries. The least complete searches will require 5,100 queries.

