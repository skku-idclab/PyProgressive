class Variable:
    def __init__(self, value):
        self.value = value
        self.projected = value
        self.degree = None

    # def __add__(self, other):        
    #     if isinstance(other, Vector):
    #         return Vector(self.x + other.x, self.y + other.y)
    #     return NotImplemented

    def __iadd__(self, other):        
        if isinstance(other, (int, float, complex)):
            self.value += other            
            return self

        if isinstance(other, Variable):
            return NotImplemented

        return NotImplemented


    def __itrue_div__(self, other):
        if isinstance(other, (int, float, complex)):
            self.value /= other
            return self

        if isinstance(other, Variable):
            return NotImplemented

        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, (int, float, complex)):
            return Variable(self.value - other)

        if isinstance(other, Variable):
            return NotImplemented

        return NotImplemented

    def __pow__(self, other):
        if isinstance(other, (int, float, complex)):
            return Variable(self.value ** other)

        if isinstance(other, Variable):
            return NotImplemented

        return NotImplemented