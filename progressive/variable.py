from .expression import Addition, Division, Multiplication, Subtraction, PowerN, print_tree, Node, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision


class Variable(Node):
    def __init__(self, loop, expr):
        self.loop = loop
        self.expr = expr
        self.modified = False

    def __iadd__(self, other):
        self.expr = InplaceAddition(self.expr, other, in_loop=self.loop.cursor_in_loop)
        self.modified = True
        return self

    def __isub__(self, other):
        self.expr = InplaceSubtraction(self.expr, other, in_loop=self.loop.cursor_in_loop)
        return self

    def __imul__(self, other):
        self.expr = InplaceMultiplication(self.expr, other, in_loop=self.loop.cursor_in_loop)
        return self

    def __itruediv__(self, other):
        self.expr = InplaceDivision(self.expr, other, in_loop=self.loop.cursor_in_loop)
        return self

    def print(self, level=0):
        print_tree(self.expr, level)

    def __str__(self):
        return f"Variable"