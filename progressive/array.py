from .token import SpecialToken, DataItemToken, DataLengthToken

class Array:
    _id = 0
    def __init__(self, data):
        self.data = data
        self.length = len(data)
        self.iter = 0
        self.id = Array._id
        Array._id += 1

    
    def __getitem__(self, index):
        if index is not SpecialToken.LOOP_INDEX:
            raise ValueError("Only loop index is supported.")
        
        return DataItemToken(self, self.id)

    def __len__(self):        
        return self.length #DataLengthToken(self)

 