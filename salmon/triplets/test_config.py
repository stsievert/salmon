from salmon.triplets.manager import Config
import pytest

html_keys = ["debrief", "instructions", "max_queries", "skip_button"]


@pytest.mark.parametrize("key", html_keys)
def test_old_html_keys(key):
    c = Config()
    with pytest.raises(ValueError, match="Move.*into the `html` key"):
        c.update({key: "foo"})


@pytest.mark.parametrize("key", html_keys)
def test_html_propogates(key):
    c = Config()

    vals = {"max_queries": 50, "skip_button": True}
    v = vals.get(key, "foobar")

    user_config = {"html": {key: v}}

    c.update(user_config)
    c = c.parse_obj(user_config)
    c.validate()

    assert c.html.dict()[key] == v


def test_defaults():
    c = Config()

    user_config = {"targets": [0, 1, 2, 3]}

    c.update(user_config)
    c = c.parse_obj(user_config)
    c.validate()

    assert c.dict() == {
        "targets": ["0", "1", "2", "3"],
        "html": {
            "instructions": "Please select the <i>comparison</i> item that is most similar to the <i>target</i> item.",
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
            "samplers_per_user": 1,
        },
    }


def test_random_old_name_warns():
    c = Config()
    user_config = {"samplers": {"RandomSampling": {}}}
    with pytest.raises(ValueError, match="renamed to `Random`"):
        c.update(user_config)


def test_wrong_probs():
    c = Config()
    user_config = {
        "samplers": {"Random": {}, "ARR": {}},
        "sampling": {"probs": {"Random": 50, "ARR": 40}},
    }
    c.update(user_config)
    c = c.parse_obj(user_config)
    with pytest.raises(ValueError, match="sampling.probs should add up to 100"):
        c.validate()


def test_wrong_keys():
    c = Config()
    user_config = {
        "samplers": {"Random": {}, "ARR_v1": {}},
        "sampling": {"probs": {"Random": 50, "ARR_v2": 50}},
    }
    c.update(user_config)
    c = c.parse_obj(user_config)
    with pytest.raises(ValueError, match="Keys in sampling.probs but not in samplers"):
        c.validate()


@pytest.mark.parametrize("v", [2, 3])
def test_bad_samplers_per_keys(v):
    c = Config()
    user_config = {
        "samplers": {"Random": {}, "ARR": {}},
        "sampling": {"samplers_per_user": v},
    }
    c.update(user_config)
    c = c.parse_obj(user_config)
    with pytest.raises(NotImplementedError, match="Only samplers_per_user in {0, 1}"):
        c.validate()


def test_d_in_common_params():
    c = Config()
    user_config = {
        "samplers": {"ARR": {}},
        "sampling": {"common": {"foo": "bar"}},
    }
    c.update(user_config)
    c = c.parse_obj(user_config)
    assert "d" in c.sampling.common and c.sampling.common["d"] == 2
