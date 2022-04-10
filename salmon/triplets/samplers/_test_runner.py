from time import sleep

from salmon.triplets.samplers._adaptive_runners import TSTE


class Test(TSTE):
    def process_answers(self, ans):
        raise Exception("Test error")
