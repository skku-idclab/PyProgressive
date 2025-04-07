from .token import SpecialToken, DataItemToken, DataLengthToken

global_arraylist = []

class Array:
    _id = 0
    def __init__(self, data):
        self.data = data
        self.length = len(data)
        self.iter = 0
        self.id = Array._id
        global_arraylist.append(self)
        Array._id += 1

    
    def __getitem__(self, index):   
        return DataItemToken(self, self.id)

    def __len__(self):        
        return self.length #DataLengthToken(self)
    
    def __str__(self):
        return "Array_" + str(self.id)
 