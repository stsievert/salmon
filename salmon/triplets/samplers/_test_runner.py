from time import sleep

from salmon.triplets.samplers._adaptive_runners import TSTE
from salmon.backend.sampler import StopRunning


class Test(TSTE):
    def process_answers(self, ans):
        raise StopRunning("Test error")
