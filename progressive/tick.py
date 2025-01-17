class Tick:
    def __init__(self, array, iter_from, iter_to):
        self.array = array
        self.iter_from = iter_from
        self.iter_to = iter_to

    def range(self):
        return range(self.iter_from, self.iter_to)
    