## Salmon
<a href="https://github.com/stsievert/salmon/actions">
  <img src="https://github.com/stsievert/salmon/actions/workflows/test.yml/badge.svg" alt="Test status badge" />
</a><a href="https://github.com/stsievert/salmon/actions">
  <img src="https://github.com/stsievert/salmon/actions/workflows/docs.yml/badge.svg" alt="Documentation status badge" />
</a>


See the documentation for more detail: https://docs.stsievert.com/salmon/

### Running Salmon offline

Visit the documentation at https://docs.stsievert.com/salmon/offline.html.
Briefly, this should work:

``` shell
$ conda env create -f salmon.yml
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
