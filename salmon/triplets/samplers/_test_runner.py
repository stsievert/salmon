from time import sleep

from ...backend.sampler import StopRunning
from ._adaptive_runners import TSTE


class Test(TSTE):
    def process_answers(self, ans):
        raise StopRunning("Test error")
