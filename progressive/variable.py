from .expression import Addition, Division, Multiplication, Subtraction, PowerN, print_tree, Node, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision


class Variable(Node):
    def __init__(self, loop, expr):
        self.loop = loop
        self.expr = expr
        self.modified = False
        self.val = None

    def __iadd__(self, other):
        raise ValueError("Inplace Operation is not supported")

    def __isub__(self, other):
        raise ValueError("Inplace Operation is not supported")

    def __imul__(self, other):
        raise ValueError("Inplace Operation is not supported")

    def __itruediv__(self, other):
        raise ValueError("Inplace Operation is not supported")

    def print(self, level=0):
        print_tree(self.expr, level)

    def value(self):
        return self.val

    def __str__(self):
        return f"Variable"