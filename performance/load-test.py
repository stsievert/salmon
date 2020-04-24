import itertools
import random

import requests
import scipy.stats as stats
from distributed.utils import sleep, time
from joblib import Parallel, delayed


def simulate_user(puid, url="http://127.0.0.1:8000", num_clicks=50):
    # Reaction times from [1, Figure 6] for "spatial configuration" task with 3
    # items (it closely mirrors the triplets task)
    #
    # 1. Palmer, E. M., Horowitz, T. S., Torralba, A., & Wolfe, J. M. (2011).
    #    What are the shapes of response time distributions in visual search?.
    #    Journal of experimental psychology. Human perception and performance,
    #    37(1), 58–71. https://doi.org/10.1037/a0020747
    reaction_times = stats.norm(0.75, 0.25)

    _start = time()
    for k in range(num_clicks):
        print(puid, k)
        q = requests.get(url + "/get_query")
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
        _start = time()
        requests.post(url + "/process_answer", json=answer)
    return puid


if __name__ == "__main__":
    url = "http://127.0.0.1:8000"
    url = "http://ec2-44-234-59-0.us-west-2.compute.amazonaws.com:8000"
    num_clicks = 50
    num_users = 100

    results = Parallel(n_jobs=num_users, backend="threading")(
        delayed(simulate_user)(seed, url=url, num_clicks=num_clicks)
        for seed in range(num_users)
    )
