from .expression import Addition, Division, Multiplication, Subtraction, PowerN

class Variable:
    def __init__(self, loop, expr):
        self.loop = loop
        self.expr = expr

    def __add__(self, other):
        return Variable(Addition(self, other))

    def __iadd__(self, other):
        self.expr = Addition(self, other)
        return self    

    def __mul__(self, other):
        return Variable(Multiplication(self, other))
    
    def __imul__(self, other):
        self.expr = Multiplication(self, other)
        return self
    
    def __sub__(self, other):
        return Variable(Subtraction(self, other))
    
    def __isub__(self, other):
        self.expr = Subtraction(self, other)
        return self    
    
    def __truediv__(self, other):
        return Variable(Division(self, other))
                
    def __itruediv__(self, other):
        self.expr = Division(self, other)
        return self
    
    def __pow__(self, other):
        if isinstance(other, int) and other > 0:
            return Variable(PowerN(self, other))