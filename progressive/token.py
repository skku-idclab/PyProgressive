from enum import Enum

class SpecialToken(Enum):
    LOOP_INDEX = 'i'


# d[i]
class DataItemToken():
    def __init__(self, array):
        self.array = array

    def __str__(self):
        return "d[i]"
        

# len(d)
class DataLengthToken():
    def __init__(self, array):
        self.array = array
    