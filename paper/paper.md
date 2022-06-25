---
title: 'Efficiently Learning Relative Similarity Embeddings with Crowdsourcing'
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
date: 09 April 2022
bibliography: paper.bib
---

# Summary

Social scientists often investigate human reasoning by collecting relative
similarity judgements with crowdsourcing services. However, this often requires
too many human responses to be practical for large experiments. To address
this problem, we introduce software called Salmon, which
makes intelligent
choices on query selection (aka active machine learning or adaptive sampling) while
collecting relative
similarity judgments from crowdsourcing participants. Salmon is usable by experimentalists
because it requires little to no programming experience and only requires an
Amazon AWS account for launching. Extensive simulations and experiments suggest
that Salmon requires 2 to 3 times fewer response than random sampling.

# Statement of need

Relative similarity judgments take the form "is item $a$ or $b$ more similar to
item $h$?" These queries work well with human working memory limitations, and have been used
successfully to characterize human perceived similarity between faces
[@faceverification], vehicles [@vehicles] and shoes [@tackl].

Typically, experimentalists require an inordinate number of human responses (about
10,000) to produce an accurate embedding when making a similarity map in
$d=2$ dimensions of $n = 50$ chemistry molecules [@chem].
The number of human responses required will change like scale like
$\mathcal{O}(nd\log n)$, which means that asking about $n=100$ molecules for $d=3$ dimensions will require about 35,000 responses.

Many "active machine learning" methods have been proposed to reduce the number
of queries required [@ckl; @ste]. These show gains, at least offline when
computation is not a limitation. However, the online deployment of
these algorithms has posed more challenges [@next].

# Related work

Systems to deploy active machine learning (ML) algorithms to crowdsourcing
audiences include SMART [@smart], NEXT [@next] and Microsoft's Multiworld Testing Decision Service [@agarwal2016multiworld].  The most relevant
related work, NEXT is capable of serving triplet queries to crowdsourcing
participants [@next]. In this work the authors concluded that "there is no
evidence for gains from adaptive sampling." However, other work has found gains from
adaptive sampling when computation is not a priority [@tackl].

Several active algorithms for triplet embedding have been developed [@ckl;
@ste]. These algorithms require searching queries and fitting the responses to
the underlying noise model. With a naive computation, scoring a single query requires $\mathcal{O}(nd)$
floating point operations (FLOPs), and the embedding typically requires significant
computation [@soe; @ma2019fast], though some work has been done to reduce the amount of computation [@erkle].

# Salmon

Salmon's main design goals are below:

1. Generate accurate relative similarity embeddings.
2. Require fewer responses than random sampling to generate an embedding.
3. Allow experimentalists to easily achieve both items above.

One method to achieve goal (2) above is to use an active machine learning
(ML) sampling algorithm. This task requires considering how to create a
responsive query page with a
service to run active ML algorithms. The result is a frontend server that
*serves* queries and *receives* answers, and a backend server that *searches*
queries and *processes* answers -- notably, not the same data flow that NEXT has
[@next], though it is common in other systems [@agarwal2016multiworld; @smart].

To verify goal (2), extensive crowdsourcing experiments and simulations have
been run, and have compared with the most relevant work [@next]. In this,
Salmon's architecture required modification of the query search algorithm to
circumvent some experimental design issues. With these modifications, we have
observed active ML algorithm gains in extensive experiments and simulations.
To the best of the author's knowledge, this is a novel achievement in the crowdsourcing context.

Goal (1) is aided by the fact that Salmon integrates a popular deep learning
framework, PyTorch [@pytorch]. This allows for easy customization of the
underlying optimization method during both online and offline computation, including by the experimentalist managing
Salmon if so desired.

Goal (3) is enabled by a relatively simple launch through Amazon AWS using Amazon Machine Images (AMIs). The AMI for Salmon[^ami] 
pulls the latest release of Salmon from GitHub and then launches Salmon. After some other tasks (e.g., opening ports, etc), Salmon is ready be launched. Salmon requires fairly minimal computational resources; all the experiments and simulation were performed with `t3.xlarge` Amazon EC2 instance, which has 4 cores, 16GB of memory and costs about $3.98 per day.

After launch, Salmon can start an experiment with stimuli consisting of text, images, video or HTML strings. It provides a mechanism to monitor an ongoing experiment, which includes the following information:

* Basic experiment statistics (e.g., number of unique users, launch date)
* Server performance (e.g., processing time for different endpoints, rate responses received)
* Crowdsourcing participant experience (e.g., new query latency)
* Embedding visualization
* List of targets.

In addition, Salmon provides links to download the responses and configuration. Salmon also supports experiment persistence through downloading and uploading experiments.
The embedding that Salmon generates can be downloaded, at least if active samplers are used. Regardless of the sampler used, Salmon can be used to generate the embeddings offline from the downloaded responses.

[^ami]:Details are at [https://docs.stsievert.com/salmon/installation][in]

[in]:https://docs.stsievert.com/salmon/installation

# Uses

Salmon has been used by several groups, including psychologists at UW--Madison,
and Louisiana State University.

# Acknowledgments

This work has been supported by the SMART Scholarship Program.

# References
