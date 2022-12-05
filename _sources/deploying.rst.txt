.. _deploying:

Deploying
=========

Most commonly, I've seen Salmon and interfaces like it deployed to
crowdsourcing services (e.g., Amazon's Mechanical Turk). With these services,
Salmon is typically deployed to these services by letting crowdsourcing
participants click on a single URL and go through various web pages before
entering a code into MTurk indicating the participant completed the study.

I have a couple recommendations for this and similar processes:

* **URL redirection.** Do not give Amazon AWS EC2 URLs/DNSs directly to
  crowdsourcing participants. Instead, give them a URL that redirects to the
  Amazon EC2 URL/DNS (e.g., via `GitHub Pages`_, ``foobar.github.io/mturk.html``).

  * This is a best practice because it avoids debugging production servers. If
    something goes wrong with your machine (like it's overloaded with too many
    users), having some redirection scheme allows redirectign crowdsourcing
    participants away from your machine.

* **Host detailed instructions/etc elsewhere.** This HTML files are typically
  shown after the crowdsourcing clicks on a link and before they see Salmon.
  (e.g., for an IRB notice). It is `technically` possible to include these
  instructions by customizing the Salmon's query page with
  :ref:`frontendcustomization`).

Hosting HTML pages is possible and relatively straighforward with `GitHub
Pages`_, as are `URL Redirections`_.

.. _URL Redirections: https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections#html_redirections

In general, I've observed some crowdsourcing trends:

* I've noticed two levels of fraud: crowdsourcing participants who submit bogus
  codes (like their Amazon MTurk ID) and those who answer responses rather
  quickly, too quickly for human response time.
* I've generally observed the responses from crowdsourcing participants to be
  high quality. I have noticed some "bad" or "junk" responses,
  and throw them out before I start my analysis.

Please `file an issue`_ or reach out `via email`_ if you have any
more deployment questions.

.. _file an issue: https://github.com/stsievert/salmon/issues/new/choose
.. _via email: mailto:stsievert@wisc.edu
.. _GitHub Pages: https://pages.github.com/
