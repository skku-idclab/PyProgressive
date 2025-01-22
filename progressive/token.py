from enum import Enum
from .expression import Addition, Subtraction, Multiplication, Division, PowerN

class SpecialToken(Enum):
    LOOP_INDEX = 'i'


# d[i]
#TODO: operator overloading (ex. s += (d[i] + 1))

class DataItemToken():
    def __init__(self, array):
        self.array = array

    def __str__(self):
        return "d[i]"
    
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
        

# len(d)
class DataLengthToken():
    def __init__(self, array):
        self.array = array
    