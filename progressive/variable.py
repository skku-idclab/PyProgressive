from .expression import Addition, Division, Multiplication, Subtraction, PowerN

# TODO: inherit from Node
class Variable:
    def __init__(self, loop, expr):
        self.loop = loop
        self.expr = expr

    def __add__(self, other):
        return Variable(self.loop, Addition(self, other))

    def __iadd__(self, other):
        self.expr = Addition(self, other)
        return self    
    
    def __radd__(self, other):
        return Variable(self.loop, Addition(other, self))

    def __mul__(self, other):
        return Variable(self.loop, Multiplication(self, other))
    
    def __imul__(self, other):
        self.expr = Multiplication(self, other)
        return self
    
    def __rmul__(self, other):
        return Variable(self.loop, Multiplication(other, self))
    
    def __sub__(self, other):
        return Variable(self.loop, Subtraction(self, other))
    
    def __isub__(self, other):
        self.expr = Subtraction(self, other)
        return self    
    
    def __rsub__(self, other):
        return Variable(self.loop, Subtraction(other, self))
    
    def __truediv__(self, other):
        return Variable(self.loop, Division(self, other))
                
    def __itruediv__(self, other):
        self.expr = Division(self, other)
        return self
    
    def __rtruediv__(self, other):
        return Variable(self.loop, Division(other, self)) 
    
    def __pow__(self, other):
        if isinstance(other, int) and other > 0:
            return Variable(self.loop, PowerN(self, other))