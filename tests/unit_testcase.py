import unittest
import pyprogressive as pp
from pyprogressive import each, accum, group, G

class TestCase1(unittest.TestCase):
    def test_grouped_accumulation(self):
        array0 = pp.array([('A', 2), ('B', 1), ('B', 4), ('C', 3), ('A', -3), ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('A', 0)])
        wholesum = accum(each(array0, 1))
        var = group(each(array0, 0), accum(each(G, 1)))
        var2 = group(each(array0, 0), accum(each(G, 1)) / accum(1))

        compiled = pp.compile(wholesum, var, var2)
        compiled.run(interval=0, callback=lambda wholesum, var, var2: print(wholesum, var, var2))
    
class TestCase2(unittest.TestCase):
    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            var = accum(each([1, "A", 3]))
            compiled = pp.compile(var)
            compiled.run(callback = lambda var: print(var))


class TestCase3(unittest.TestCase):
    def test_empty_array(self):
        empty_array = pp.array([])
        with self.assertRaises(ValueError):
            var = accum(each(empty_array))
            compiled = pp.compile(var)
            compiled.run(callback=lambda var: print(var))


if __name__ == '__main__':
    unittest.main()

    
