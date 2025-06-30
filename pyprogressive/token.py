from enum import Enum
from .expression import Addition, Subtraction, Multiplication, Division, PowerN
from .array import global_arraylist

global_G_arridx = None

class SpecialToken(Enum):
    LOOP_INDEX = 'i'


# d[i]

class DataItemToken():
    def __init__(self, array, id, index = -1):
        self.array = array
        self.id = id
        self.index = index # this is for tuple array

    def __str__(self):
        return "d[i]_"+str(self.id)
    
    def __add__(self, other):
        # d[i] + other => Addition(self, other)
        return Addition(self, other)

    def __radd__(self, other):
        # other + d[i] => Addition(other, self)
        return Addition(other, self)
    
    def __sub__(self, other):
        # d[i] - other => Subtraction(self, other)
        return Subtraction(self, other)
    
    def __rsub__(self, other):
        # other - d[i] => Subtraction(other, self)
        return Subtraction(other, self)
    
    def __mul__(self, other):
        # d[i] * other => Multiplication(self, other)
        return Multiplication(self, other)
    
    def __rmul__(self, other):
        # other * d[i] => Multiplication(other, self)
        return Multiplication(other, self)
    
    def __truediv__(self, other):
        # d[i] / other => Division(self, other)
        return Division(self, other)
    
    def __rtruediv__(self, other):
        # other / d[i] => Division(other, self)
        return Division(other, self)
    
    def __pow__(self, other):
        # d[i] ** other => PowerN(self, other)
        return PowerN(self, other)
    
    def __len__(self):
        return len(self.array)
    
    def print(self):
        print("d[i]_"+str(self.id))
        

# length of array, it can be estimated when using groupby
class DataLengthToken():
    def __init__(self, array = None, arrayid = None, value = None, ingroup = False):
        if array is not None:
            self.array = array
            self.arrayid = array.id
 
            self.value = value if value is not None else len(array.data)
        elif arrayid is not None:
            self.array = None 
            self.arrayid = arrayid

            found_array = next((a for a in global_arraylist if a.id == arrayid), None)
            self.value = value if value is not None else (len(found_array.data) if found_array else None)

        else:
            raise ValueError("DataLengthToken requires either an array object or an arrayid.")


        self.ingroup = ingroup
    def __str__(self):
        return "LengthToken_"+str(self.arrayid)
    

class GToken: # Token for GroupBy
    def __init__(self, access_index = None):
        self.access_index = access_index
    def __str__(self):
        return f"GToken_{self.access_index}"