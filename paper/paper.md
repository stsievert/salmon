---
title: 'Salmon: Efficient Crowdsourcing for Relative Similarity Judgments'
tags:
  - crowdsourcing
  - active machine learning
  - relatively similarity
  - adaptive sampling
authors:
  - name: Scott Sievert
    orcid: 0000-0002-4275-3452
    affiliation: 1
affiliations:
 - name: University of Wisconsin--Madison
   index: 1
date: 20 April 2021
bibliography: paper.bib
---

# Summary

Social scientists often investigate human reasoning by collecting relative similarity
judgements with crowdsourcing services. However, this often requires too
many human responses to be practical for larger experiments. To address this
problem, we introduce a software called Salmon. Salmon collects
relative similarity judgments from crowdsourcing participants and makes
intelligent choices about which queries to ask next. Salmon is usable by
experimentalists because it requires little to no programming experience and
 only requires an Amazon AWS account for launching. Extensive simulations and
experiments reveal that Salmon requires 2 to 3 times fewer response than random sampling.

# Statement of need

Relative similarity judgments take the form "is item $a$ or $b$ more similar to
item $h$?" These queries work with human working memory, and have been used
successfully to characterize human perceived similarity between faces [@faceverification],
vehicles [@vehicles] and shoes [@tackl].

Experimentalists required an inordinate number of human responses (about $10,000$)
to produce an accurate embedding when making a similarity map in $d=2$ dimensions
of $n = 50$ chemistry molecules [@chem]. The number of responses
required will grow like $\mathcal{O}(nd\log n)$ as $n$ and $d$ are changed
[@jain2016finite; @jamieson2011low].

Many "active machine learning" methods have been proposed to reduce the number
of queries required [@ckl; @ste]. These show gains, at least
offline when computation is not a limitation [@erkle]. However, the online
deployment of these algorithms has posed more challenges [@next].

# Related work

Systems to deploy active machine learning (ML) algorithms to crowdsourcing audiences include [@smart; @next; @agarwal2016multiworld].  The most relevant
related work is capable of serving triplet queries to crowdsourcing
participants [@next]. In this work the authors concluded that "there is no
evidence for gains from adaptive sampling." Other work has found gains from
adaptive sampling in offline computation is not an issue [@tackl], suggesting
that there are some gains for the triplet embedding problem.

Several active algorithms for triplet embedding have been developed[@ckl;
@ste]. These algorithms require searching queries and fitting the responses to
the underlying noise model. Scoring a single query requires $\mathcal{O}(nd)$
floating point operations (FLOPs), and the embedding requires
significant computation [@soe; @ma2019fast].

# Salmon

Salmon's main design goals are below:


1. Require fewer responses than random sampling to generate an accurate
   relative similarity embedding.
2. Generate accurate embeddings.
3. Enable experimentalists to achieve both goals above.

One method to achieve goal (1) above is to use an "active machine learning"
sampling algorithm. This task required consideration of how to create a
responsive query page with a
service to run active ML algorithm. The result is a frontend server for
*serving* queries and *receives* answers, and a backend server that *searches*
queries and *processes* answers -- notably, not the same data flow that NEXT has
[@next], though it is common in other systems [@agarwal2016multiworld; @smart].

Goal (2) is aided by the fact that Salmon integrates a popular deep learning
framework, PyTorch [@pytorch]. This allows for easy customization of the
underlying optimization method, including by the experimentalist managing
Salmon and during generation of offline embeddings.

Goal (3) is enabled by a relatively simple launch through Amazon AWS, which
pulls the latest release of Salmon from GitHub and then launches the Salmon
servers. This is relatively simple, thanks to simple dependency management
though Docker containers. Docker is a natural fit because the required Redis
database is easiest to launch through with a Docker container.

To verify goal (1), we ran extensive simulations and experiments and compared
with the most relevant work [@next]. In this, Salmon's architecture required
modification of the query search algorithm to circumvent some experimental
design issues. With these modifications, we have observed active ML algorithm
gains in extensive experiments and simulations. For this experiment in the
crowdsourcing context, this is a novel achievement [@next].

# Uses

Salmon has been used by several groups, including psychologists at UW--Madison
to measure player perceived similarity between video games and by psychologists
at Louisiana State University.

# Acknowledgments

The author is supported by the SMART Scholarship Program.

# References
