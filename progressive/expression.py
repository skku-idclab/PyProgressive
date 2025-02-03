
class Node:
    """represents a node in the expression tree"""
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return self.__class__.__name__

    def __add__(self, other):
        return Addition(self, other)

    def __radd__(self, other):
        return Addition(other, self)


    def __mul__(self, other):
        return Multiplication(self, other)


    def __rmul__(self, other):
        return Multiplication(other, self)


    def __sub__(self, other):
        return Subtraction(self, other)


    def __rsub__(self, other):
        return Subtraction(other, self)


    def __truediv__(self, other):
        return Division(self, other)


    def __rtruediv__(self, other):
        return Division(other, self)

    def __pow__(self, other):
        if isinstance(other, int) and other > 0:
            return PowerN(self, other)

        raise ValueError("Only positive integer exponents are supported")

    def print(self, level=0):
        print_tree(self, level)

class BinaryOperationNode(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Addition(BinaryOperationNode):
    pass

class Subtraction(BinaryOperationNode):
    pass

class Multiplication(BinaryOperationNode):
    pass

class Division(BinaryOperationNode):
    pass

class PowerN(Node):
    def __init__(self, base, exponent):
        self.base = base
        self.exponent = exponent


class InplaceOperationNode(Node):
    def __init__(self, left, right, in_loop):
        self.left = left
        self.right = right
        self.in_loop = in_loop

    def __str__(self):
        return f"{self.__class__.__name__} {'(In Loop)' if self.in_loop else ''}"

class InplaceAddition(InplaceOperationNode):
    pass

class InplaceSubtraction(InplaceOperationNode):
    pass

class InplaceMultiplication(InplaceOperationNode):
    pass

class InplaceDivision(InplaceOperationNode):
    pass


class Constantized(Node):
    _counter = 0

    def __init__(self, expr):
        super().__init__(expr)
        self.expr = expr
        self.id = Constantized._counter
        Constantized._counter += 1
    def __str__(self):
        return f"Constantized_var{self.id}"


def print_tree(node, level=0):
    """
    Prints the hierarchy of the tree starting from the given node.

    Args:
        node (Node): The root node of the tree.
        level (int): Current level in the tree hierarchy (used for indentation).
    """
    if node is None:
        return

    # Print the current node with indentation
    print("--" * level + f"{node}")

    # Recursively print left and right children if they exist
    if isinstance(node, (Addition, Subtraction, Multiplication, Division)):
        print_tree(node.left, level + 1)
        print_tree(node.right, level + 1)
    elif isinstance(node, (InplaceAddition, InplaceDivision, InplaceMultiplication, InplaceSubtraction)):
        print_tree(node.left, level + 1)
        print_tree(node.right, level + 1)
    elif isinstance(node, PowerN):
        print_tree(node.base, level + 1)
        print_tree(node.exponent, level + 1)
    elif isinstance(node, Constantized):
        print_tree(node.expr, level + 1)
    elif isinstance(node, Node):
        node.print(level + 1)
