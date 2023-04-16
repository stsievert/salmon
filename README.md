## Salmon
<a href="https://github.com/stsievert/salmon/actions/workflows/test.yml">
 <img src="https://github.com/stsievert/salmon/actions/workflows/test.yml/badge.svg?branch=master" />
</a>
<a href="https://github.com/stsievert/salmon/actions/workflows/test_pip.yml">
 <img src="https://github.com/stsievert/salmon/actions/workflows/test_pip.yml/badge.svg?branch=master" />
</a>
<a href="https://github.com/stsievert/salmon/actions/workflows/test_offline.yml">
  <img src="https://github.com/stsievert/salmon/actions/workflows/test_offline.yml/badge.svg?branch=master" />
</a>
<a href="https://github.com/stsievert/salmon/actions/workflows/docs.yml">
  <img src="https://github.com/stsievert/salmon/actions/workflows/docs.yml/badge.svg?branch=master" />
</a>

Salmon is a tool for efficiently generating ordinal embeddings. It relies on
"active" machine learning algorithms to choose the most informative queries for
humans to answer.

### Documentation

This documentation is available at these locations:

- **Primary source**: https://docs.stsievert.com/salmon/
- Secondary source: as [a raw PDF][pdf] (and as a [slower loading PDF][blobpdf]).
- Secondary source: as [zipped HTML directory][ziphtml], which requires unzipping the directory
  then opening up `index.html`.

[pdf]:https://github.com/stsievert/salmon/raw/gh-pages/salmon.pdf
[blobpdf]:https://github.com/stsievert/salmon/blob/gh-pages/salmon.pdf
[ziphtml]:https://github.com/stsievert/salmon/archive/refs/heads/gh-pages.zip

Please [file an issue][issue] if you can not access the documentation.

[issue]:https://github.com/stsievert/salmon/issues/new

### Running Salmon offline
Visit the documentation at https://docs.stsievert.com/salmon/offline.html.
Briefly, this should work:

``` shell
$ cd path/to/salmon
$ conda env create -f salmon.lock.yml
$ conda activate salmon
(salmon) $ pip install -e .
```

The documentation online mentions more about how to generate an embedding
offline: https://docs.stsievert.com/salmon/offline.html#generate-embeddings

With this, it's also possible to create a script that uses and imports Salmon:

``` python
from salmon.triplets.samplers import TSTE
import numpy as np

n, d = 85, 2
sampler = TSTE(n=n, d=d)

em_init = np.array([[i, -i] for i in range(n)])
sampler.opt.initialize(embedding=em_init)

queries, scores, meta = sampler.get_queries(num=10_000)
```

This script allows the data scientist to score queries for an embedding they
specify.

[semver]:https://semver.org
