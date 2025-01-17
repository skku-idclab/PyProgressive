class Array:
    def __init__(self, data):
        self.data = data
        self.length = len(data)

        self.iter = 0

    def init_iter(self):
        self.iter = 0

    def update_iter(self, iter):
        self.iter = iter

    def iter_done(self):
        return self.iter >= self.length
    
    def __getitem__(self, index):
        return self.data[index]    

    def __len__(self):
        ## this should be changed
        return self.length

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < self.length:
            self.index += 1
            return self.data[self.index - 1]
        else:
            raise StopIteration
    
    def range(self):
        return range(self.length)