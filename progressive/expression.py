
class Node:
    pass

class Addition(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Multiplication(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        
class Subtraction(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
class Division(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        
class PowerN(Node):
    def __init__(self, base, exponent):
        self.base = base
        self.exponent = exponent
        