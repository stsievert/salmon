import pytest

from salmon.triplets.manager import Config

html_keys = ["debrief", "instructions", "max_queries", "skip_button"]


@pytest.mark.parametrize("key", html_keys)
def test_old_html_keys_warns(key):
    c = Config()
    with pytest.raises(ValueError, match="Move.*into the `html` key"):
        c.parse({key: "foo"})


@pytest.mark.parametrize("key", html_keys)
def test_html_propogates(key):
    vals = {"max_queries": 50, "skip_button": True}
    v = vals.get(key, "foobar")

    user_config = {"html": {key: v}}
    c = Config().parse(user_config)

    assert c.html.dict()[key] == v


def test_defaults():
    user_config = {"targets": [0, 1, 2, 3]}
    c = Config().parse(user_config)

    assert c.dict() == {
        "targets": ["0", "1", "2", "3"],
        "html": {
            "instructions": "Please select the <i>comparison</i> item that is most similar to the <i>target</i> item.",
            "title": "Similarity judgements",
            "debrief": "<b>Thanks!</b> Please use the participant ID below.",
            "skip_button": False,
            "css": "",
            "max_queries": 50,
            "arrow_keys": True,
        },
        "samplers": {"random": {"class": "Random"}},
        "sampling": {
            "common": {"d": 2},
            "probs": {"random": 100},
            "samplers_per_user": 0,
        },
    }


def test_random_old_name_warns():
    user_config = {"samplers": {"RandomSampling": {}}}
    c = Config()
    with pytest.raises(ValueError, match="renamed to `Random`"):
        c.parse(user_config)


def test_wrong_probs():
    user_config = {
        "samplers": {"Random": {}, "ARR": {}},
        "sampling": {"probs": {"Random": 50, "ARR": 40}},
    }
    c = Config()
    with pytest.raises(ValueError, match="sampling.probs should add up to 100"):
        c.parse(user_config)


def test_wrong_keys():
    user_config = {
        "samplers": {"Random": {}, "ARR_v1": {}},
        "sampling": {"probs": {"Random": 50, "ARR_v2": 50}},
    }
    c = Config()
    with pytest.raises(ValueError, match="Keys in sampling.probs but not in samplers"):
        c.parse(user_config)


@pytest.mark.parametrize("v", [0, 1, 2, 3])
def test_bad_samplers_per_keys(v):
    c = Config()
    user_config = {
        "samplers": {"Random": {}, "ARR": {}},
        "sampling": {"samplers_per_user": v},
    }
    if v in [0, 1]:
        c.parse(user_config)
    else:
        with pytest.raises(
            NotImplementedError, match="Only samplers_per_user in {0, 1}"
        ):
            c.parse(user_config)


def test_d_default_in_common_params():
    user_config = {
        "samplers": {"ARR": {}},
        "sampling": {"common": {"foo": "bar"}},
    }
    c = Config().parse(user_config)
    assert c.sampling.common == {"d": 2, "foo": "bar"}


def test_d_default_updates():
    user_config = {
        "samplers": {"ARR": {}, "TSTE": {}},
        "sampling": {"common": {"d": 3}},
    }
    c = Config().parse(user_config)
    assert c.sampling.common == {"d": 3}

    user_config = {
        "samplers": {"ARR": {}, "TSTE": {}},
        "sampling": {"common": {"d": 3, "foo": "bar"}},
    }
    c = Config().parse(user_config)
    assert c.sampling.common == {"d": 3, "foo": "bar"}


def test_probs_default():
    user_config = {"samplers": {"ARR": {}, "TSTE": {}}}
    c = Config().parse(user_config)
    assert c.sampling.probs == {"ARR": 50, "TSTE": 50}
