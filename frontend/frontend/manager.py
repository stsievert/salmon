from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel

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
    name: str
    score: float
    puid: str = ""
    response_time: float = -1
    network_latency: float = -1



def get_responses(answers: List[Dict[str, Any]], targets, start_time=0):
    start = start_time
    out = []
    for datum in answers:
        out.append(datum)
        datetime_received = timedelta(seconds=datum["time_received"]) + datetime(
            1970, 1, 1
        )
        idxs = {
            key + "_object": targets[datum[key]]
            for key in ["left", "right", "head", "winner"]
        }
        names = {
            key + "_filename": _get_filename(idxs[f"{key}_object"])
            for key in ["left", "right", "head", "winner"]
        }
        meta = {
            "time_received_since_start": datum["time_received"] - start,
            "datetime_received": datetime_received.isoformat(),
        }
        out[-1].update({**idxs, **names, **meta})
    return out

def _get_filename(html):
    html = str(html)
    if "<img" in html or "<video" in html:
        i = html.find("src=")
        j = html[i:].find(" ")
        return html[i + 5 : i + j - 1].replace("/static/targets/", "")
    return html
