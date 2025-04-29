class NormalizedFirstMoment():
    def __init__(self):
        self.value = 0
        self.count = 0        

    def accumulate(self, value):
        self.value += value
        self.count += 1