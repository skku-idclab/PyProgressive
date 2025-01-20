from .expression import Addition, Division, Multiplication, Subtraction, PowerN, print_tree, Node

class Variable(Node):
    def __init__(self, loop, expr):
        self.loop = loop
        self.expr = expr
    
    def __iadd__(self, other):        
        self.expr = Addition(self.expr, other)
        return self    
    
    def __isub__(self, other):
        self.expr = Subtraction(self.expr, other)
        return self    
    
    def __imul__(self, other):
        self.expr = Multiplication(self.expr, other)
        return self

    def __itruediv__(self, other):
        self.expr = Division(self.expr, other)
        return self
    
    def print(self):
        print_tree(self.expr)

    def __str__(self):
        return self.expr.__str__()