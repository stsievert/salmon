from time import sleep

from ._adaptive_runners import TSTE
from ...backend.sampler import StopRunning


class Test(TSTE):
    def process_answers(self, ans):
        raise StopRunning("Test error")
