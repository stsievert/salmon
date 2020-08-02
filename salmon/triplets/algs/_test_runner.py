from time import sleep
from ._random_sampling import RandomSampling

class Test(RandomSampling):
    def __init__(self, *args, **kwargs):
        self.counter = 0
        super().__init__(*args, **kwargs)

    def process_answers(self, ans):
        if self.counter:
            sleep(1)
        self.counter += 1
        raise Exception("Test error")
