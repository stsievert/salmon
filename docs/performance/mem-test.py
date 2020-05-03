import os
import itertools
import random
from pathlib import Path
from time import sleep
from typing import List

import requests
import scipy.stats as stats
from distributed.utils import time
from joblib import Parallel, delayed
import pandas as pd


def simulate_user(puid, url="http://127.0.0.1:8421", num_clicks=50):
    # Reaction times from [1, Figure 6] for "spatial configuration" task with 3
    # items (it closely mirrors the triplets task)
    #
    # 1. Palmer, E. M., Horowitz, T. S., Torralba, A., & Wolfe, J. M. (2011).
    #    What are the shapes of response time distributions in visual search?.
    #    Journal of experimental psychology. Human perception and performance,
    #    37(1), 58–71. https://doi.org/10.1037/a0020747
    reaction_times = stats.norm(0.75, 0.25)

    _start = time()
    answers = []
    for k in range(num_clicks):
        print(puid, k)
        q = requests.get(url + "/query")
        network_latency = time() - _start
        query = q.json()
        winner = random.choice([query["left"], query["right"]])
        reaction_time = max(0.2, reaction_times.rvs())
        sleep(reaction_time)

        answer = {
            "winner": winner,
            "puid": puid,
            "response_time": reaction_time,
            "network_latency": network_latency,
            **query,
        }
        answers.append(answer)
        _start = time()
        requests.post(url + "/answer", json=answer)
    return answers


if __name__ == "__main__":
    url = "http://127.0.0.1:8421"
    num_clicks = 50
    num_users = 100

    exp_file = Path(__file__).absolute().parent / "exp-many-targets.yaml"
    salmon_pword = os.environ.get("SALMON_PWORD")
    username, password = "foo", salmon_pword
    kwargs = dict(auth=(username, password))
    r = requests.delete(url + "/reset?force=1", **kwargs)
    assert r.status_code == 200
    r = requests.post(url + "/init_exp", data={"exp": exp_file.read_bytes()}, **kwargs)
    assert r.status_code == 200

    results = Parallel(n_jobs=num_users, backend="threading")(
        delayed(simulate_user)(seed, url=url, num_clicks=num_clicks)
        for seed in range(num_users)
    )
    all_results: List[dict] = sum(results, [])
    df = pd.DataFrame(all_results)
