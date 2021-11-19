from copy import deepcopy
from textwrap import dedent
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, BaseSettings, Field, validator


class Answer(BaseModel):
    """
    An answer to a triplet query. head, left and right are integers
    from '/get_query'. The 'winner' is an integer that is most similar to 'head',
    and must be one of 'left' and 'right'.

    'puid' is the "participant unique ID", and is optional.

    """

    head: int
    left: int
    right: int
    winner: int
    alg_ident: str
    score: float = 0
    puid: str = ""
    response_time: float = -1
    network_latency: float = -1


class Sampling(BaseSettings):
    """
    Settings to configure how more than two samplers are used.

    These settings are used in the HTML but are not stylistic. The
    exception is ``common``, which is passed to every ``sampler`` during
    initialization and will likely be optional arguments for
    :class:`~salmon.triplets.samplers.Adaptive`.

    The default config represented as a YAML file:

    .. code-block:: yaml

       sampling:
         common: {"d": 2}
         probs: {"random": 100}
         samplers_per_user: 1

    """

    common: Dict[str, Any] = Field(
        {"d": 2},
        description="""Arguments to pass to every sampler for initialization (likely
        values for :class:`~salmon.triplets.samplers.Adaptive`; note that
        values for ``n`` and ``ident`` are already specified). Any
        values specified in this field will be overwritten by
        sampler-specific arguments.""",
    )
    probs: Optional[Dict[str, int]] = Field(
        None,
        description="""The percentage to sample each ``sampler`` when given the
        opportunity (which depends on ``samplers_per_user``). The percentages
        in this sampler must add up to 100.
        If not specified (default), choose each sampler with equal
        probability.""",
    )
    samplers_per_user: int = Field(
        1,
        description="""The number of samplers to assign to each user. Setting
        ``samplers_per_user=1`` means any user only sees queries generated
        from one sampler, and ``sampler_per_user=0`` means the user sees a
        new sampler every query""",
    )


class HTML(BaseSettings):
    """
    Stylistic settings to configure the HTML page.

    The default configuration in YAML:

    .. code-block:: yaml

       html:
         instructions: Please select the <i>comparison</i> item that is most similar to the <i>target</i> item.
         debrief: "<b>Thanks!</b> Please use the participant ID below."
         skip_button: false
         css: ""
         max_queries: 50
         arrow_keys: true
    """

    instructions: str = Field(
        "Please select the <i>comparison</i> item that is most similar to the <i>target</i> item.",
        description="The instructions the user sees above each query.",
    )
    debrief: str = Field(
        "<b>Thanks!</b> Please use the participant ID below.",
        description=dedent(
            """The message that the user sees after ``max_queries`` responses
            have been completed. The participant ID (``puid``) is shown below
            this message."""
        ),
    )
    skip_button: bool = Field(
        False,
        description="""Wheter to show a button to skip queries. Most
        useful when participants are instructed to skip queries only when the
        know nothing about any object.""",
    )
    css: str = Field(
        "",
        description="""CSS to be included the in the query page.  This CSS is
        inserted just before the ``</style>`` tag in the HTML head.""",
    )
    max_queries: int = Field(
        50,
        description="""The number of queries that the user will answer before
        seeing the ``debrief`` message). Set ``max_queries=0`` or
        ``max_queries=-1`` to ask unlimited queries.""",
    )
    arrow_keys: bool = Field(
        True,
        description="""Wheter to allow using the arrow keys as input.  Specifying
        ``arrow_keys=True`` might allow bad input (though there is a delay of
        200ms between queries).""",
    )


class Config(BaseSettings):
    """
    Customization of Salmon sampling and HTML.

    This class is often specified through uploading an ``init.yaml`` file as
    described in :ref:`yamlinitialization`. The default config is given below:

    .. code-block:: yaml

       samplers:
         random: {class: Random}
       sampling:
         probs: {"random": 100}
         sampler_per_user: 1
         common:
           d: 2
       html:
         instructions: Please select the <i>comparison</i> item that is most similar to the <i>target</i> item.
         debrief: <b>Thanks!</b> Please use the participant ID below.
         skip_button: false
         css: ""
         arrow_keys: true
       targets: ["vonn", "<i>Kildow</i>", "lindsey", "ted"]  # actually required

    Some details on specific fields:

    * The only required field is targets.

        * ``targets`` is often specified with the upload of a ZIP file. See
          :ref:`yaml_plus_zip` for more detail. If not, specify a list of strings (which
          will be rendered as HTML).

    * ``sampling`` is not relevant until ``samplers`` is customized.

    Here's how to customize the config a bit with
    a YAML file:

    .. code-block:: yaml

       samplers:
         testing: {class: Random}
         ARR: {}
         Validation:
           n_queries: 20
       sampling:
         probs: {"ARR": 40, "Validation": 20, "testing": 20}
         common:
           d: 3  # dimensions to embed to; passed to every sampler
           random_state: 42  # argument to Adaptive
           initial_batch_size: 128  # argument to Embedding
       html:
         instructions: Click buttons, <b><i>or else.</i></b>

    Full documentation is below.

    """

    targets: Optional[Union[int, List[str]]] = Field(
        None,
        description="""A list of targets that will be rendered as HTML. If a ZIP file is
            uploaded, this field is populated automatically.
            See :ref:`yaml_plus_zip` for more detail.""",
    )
    html: HTML = Field(
        HTML(),
        description="""Stylistic settings to configure the HTML page.
            See :class:`~salmon.triplets.manager.HTML` for more detail.""",
    )
    samplers: dict = Field(
        {"random": {"class": "Random"}},
        description="""Samplers to use, and their initialization parameters. See
            above or ":ref:`adaptive-config`" for more detail on
            customization, and :ref:`experiments` for experiments/benchmarks.""",
    )
    sampling: Sampling = Field(
        Sampling(),
        description="""Settings to configure how more than two samplers are
        used. See :class:`~salmon.triplets.manager.Sampling` for more detail.""",
    )


    def update(self, user_config):
        # Update user_config so when updated below, changes reflected.
        # (it's a plain dict, so it needs some help)
        if "sampling" in user_config and "common" in user_config["sampling"]:
            s = self.dict()["sampling"]["common"]
            user_config["sampling"]["common"].update(self.dict()["sampling"]["common"])

        self._warn(user_config)
        return self

    def validate(self):
        if self.sampling.probs is None:
            # Sample each sampler equally
            n = len(self.samplers)
            freqs = [100 // n,] * n
            freqs[0] += 100 % n  # because integer division might be off by one
            sampling_percent = {k: f for k, f in zip(self.samplers, freqs)}
            self.sampling.probs = sampling_percent

        if set(self.sampling.probs.keys()) != set(self.samplers.keys()):
            sf = set(self.sampling.probs)
            s = set(self.samplers)
            msg = (
                "sampling.probs keys={} are not the same as samplers keys={}.\n\n"
                "Keys in sampling.probs but not in samplers: {}\n"
                "Keys in samplers but but in sampling.probs: {}\n\n"
            )
            raise ValueError(msg.format(sf, s, sf - s, s - sf))

        if (v := self.sampling.samplers_per_user) not in {0, 1}:
            raise NotImplementedError(
                "Only samplers_per_user in {0, 1} is implemented, not "
                f"samplers_per_user={v}"
            )

        if sum(self.sampling.probs.values()) != 100:
            msg = (
                "The values in sampling.probs should add up to 100; however, "
                "the passed sampling.probs={} adds up to {}"
            )
            s2 = self.sampling.probs
            raise ValueError(msg.format(s2, sum(s2.values())))

    def _warn(self, config):
        # TODO: deprecate
        html = self.html.dict()
        if any(h in config for h in html.keys()):
            misplaced_keys = [h for h in config if h in html]
            misplaced = [f"{h}: {config[h]}" for h in misplaced_keys]
            fmt_misplace = "\n  ".join(list(sorted(misplaced)))
            msg = (
                f"Move keys {misplaced_keys} into the `html` key. That is, include "
                f"this block of YAML:\n\nhtml:\n  {fmt_misplace}\n"
            )
            raise ValueError(msg)

        if "RandomSampling" in config.get("samplers", ""):
            raise ValueError(
                "The sampler `RandomSampling` has been renamed to `Random`."
            )


def deserialize_query(serialized_query: str) -> Dict[str, int]:
    h, l, r = serialized_query.split("-")
    flip = random.choice([True, False])
    if flip:
        l, r = r, l
    return {
        "head": int(h),
        "left": int(l),
        "right": int(r),
    }


def get_responses(answers: List[Dict[str, Any]], targets, start_time=0):
    start = start_time
    out = []
    for datum in answers:
        out.append(datum)
        datetime_received = timedelta(seconds=datum["time_received"]) + datetime(
            1970, 1, 1
        )
        idxs = {
            key + "_html": targets[datum[key]]
            for key in ["left", "right", "head", "winner", "loser"]
        }
        names = {
            key + "_filename": _get_filename(idxs[f"{key}_html"])
            for key in ["left", "right", "head", "winner", "loser"]
        }
        meta = {
            "time_received_since_start": datum["time_received"] - start,
            "datetime_received": datetime_received.isoformat(),
            "start_time": start_time,
        }
        out[-1].update({**idxs, **names, **meta})
    return out


def random_query(n: int) -> Dict[str, int]:
    rng = np.random.RandomState()
    while True:
        a, b, c = rng.choice(n, size=3)
        if a != b and b != c and c != a:
            break
    return {
        "head": int(a),
        "left": int(b),
        "right": int(c),
    }


def _get_filename(html):
    html = str(html)
    if "<img" in html or "<video" in html:
        i = html.find("src=")
        j = html[i:].find(" ")
        return html[i + 5 : i + j - 1].replace("/static/targets/", "")
    return html
