from typing import Tuple, List, Dict
from dataclasses import dataclass

Answer = Tuple[int, Tuple[int, int]]


@dataclass
class Query:
    head: int
    left: int
    right: int
    winner: int
