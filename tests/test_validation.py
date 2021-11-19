import pytest

from .utils import LogError, logs, server


def test_init_w_queries_valid_idx(server, logs):
    samplers = {"Validation": {"queries": [[0, 1, 4], [0, 1, 5]]}}
    exp = {"targets": [0, 1, 2, 3], "samplers": samplers}

    with pytest.raises(LogError), logs:
        server.authorize()
        server.get("/init")
        r = server.post("/init_exp", data={"exp": exp}, error=True)
        assert r.status_code == 500
        assert "the index 5 is included" in r.text.lower()
        assert "the n=4 targets" in r.text.lower()
