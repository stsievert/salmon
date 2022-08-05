# Triplet dataset
Files:

* `all_triplets.csv`: raw MTurk responses.
    * Has header `head, b, c` (=> `head, close, far`)
* `deconflicted_triplets.csv`: deconflicted
    * ordered `(head, b, c)` so that `b` closer to `head` than `c`
    * => ordering should be `(head,close,far)`
* `cnn_feats.csv`: looks like feature for each shoe from a CNN.


From email with Matthew Berger:

```
From: Scott Sievert <stsievert@wisc.edu>
Subject: Re: Zappos triplet dataset
Date: Tuesday, March 27, 2018 at 1:17:14 PM Central Daylight Time
To: Matthew Berger <matthew.sh.berger@gmail.com>
CC: ROBERT D NOWAK <rdnowak@wisc.edu>, eric@cs.pitt.edu, lee.seversky@us.af.mil, milos@cs.pitt.edu

Hi Scott,

Sure thing, you can find the data here:

hdc.cs.arizona.edu/people/berger/triplet/zappos.zip

- The deconflicted_triplets.csv file contains the triplet responses where we
  have filtered triplets that resulted in inconsistencies, by analyzing the
  graph formed by triplets and removing cycles. Each line is ordered as (a,b,c)
  such that b is more similar to a than c is more similar to a.
- cnn_feats.csv contains (AlexNet) CNN features for each of the corresponding
  images. The line numbers correspond to the indices in the triplets csv file.
- The images directory contains the images for each object, where the filename
  corresponds to the index in the triplets csv file.

If you are also interested in the raw triplet data that we collected through AMT please let us know.

In addition, we have collected triplets through AMT for several other datasets that you might find of interest. First, we have collected triplets for the Animals with Attributes dataset, first popularized in the following paper:

https://cvml.ist.ac.at/AwA/

Secondly, we have collected triplets for the CUB dataset:

http://www.vision.caltech.edu/visipedia/CUB-200.html

Let us know if you think triplets for these datasets would be useful for your research, and we’d be happy to share the data.

Best,

Matt

```

This data was downloaded from http://hdc.cs.arizona.edu/people/berger/triplet/zappos.zip
