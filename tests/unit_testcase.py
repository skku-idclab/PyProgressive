import unittest
import pyprogressive as pp
from pyprogressive import each, accum, group, G


class TestCase1(unittest.TestCase):
    """Grouped accumulation with tuple array."""
    def setUp(self):
        pp.reset()

    def test_grouped_sum_and_mean(self):
        array0 = pp.array([('A', 2), ('B', 1), ('B', 4), ('C', 3),
                           ('A', -3), ('A', 10), ('A', 8), ('B', 7),
                           ('A', 10), ('A', 0)])
        wholesum = accum(each(array0, 1))
        var  = group(each(array0, 0), accum(each(G, 1)))
        var2 = group(each(array0, 0), accum(each(G, 1)) / accum(1))

        compiled = pp.compile(wholesum, var, var2)
        for state in compiled.run(interval=0):
            pass

        # wholesum = N * E[X] = sum of all values
        self.assertAlmostEqual(state.value(wholesum), 42.0, places=6)

        # group sum
        result_sum = state.value(var)
        self.assertAlmostEqual(result_sum['A'], 27.0, places=6)
        self.assertAlmostEqual(result_sum['B'], 12.0, places=6)
        self.assertAlmostEqual(result_sum['C'],  3.0, places=6)

        # group mean
        result_mean = state.value(var2)
        self.assertAlmostEqual(result_mean['A'], 27.0 / 6, places=6)
        self.assertAlmostEqual(result_mean['B'], 12.0 / 3, places=6)
        self.assertAlmostEqual(result_mean['C'],  3.0 / 1, places=6)

    def test_done_and_progress(self):
        arr = pp.array([1, 2, 3, 4, 5])
        var = accum(each(arr)) / len(arr)
        compiled = pp.compile(var)
        for state in compiled.run(interval=0):
            pass
        self.assertTrue(state.done)
        self.assertAlmostEqual(state.progress, 1.0, places=6)


class TestCase2(unittest.TestCase):
    """Input validation."""
    def setUp(self):
        pp.reset()

    def test_non_array_raises(self):
        with self.assertRaises(ValueError):
            each([1, 2, 3])   # plain list, not pp.array

    def test_non_homogeneous_tuple_raises(self):
        # mix of tuple and non-tuple triggers the homogeneity check in each()
        arr = pp.array([(1, 2), 3, (4, 5)])
        with self.assertRaises(ValueError):
            each(arr, 1)


class TestCase3(unittest.TestCase):
    """Empty array handling."""
    def setUp(self):
        pp.reset()

    def test_empty_array_raises(self):
        empty = pp.array([])
        var = accum(each(empty))
        compiled = pp.compile(var)
        with self.assertRaises((ValueError, UnboundLocalError)):
            for state in compiled.run(interval=0):
                pass


class TestCase4(unittest.TestCase):
    """Multi-array sum."""
    def setUp(self):
        pp.reset()

    def test_element_wise_sum(self):
        arr1 = pp.array([1, 2, 3])
        arr2 = pp.array([4, 5, 6])
        var = accum(each(arr1) + each(arr2))
        compiled = pp.compile(var)
        for state in compiled.run(interval=0):
            pass
        # accum(each(arr1)+each(arr2)) = N * E[X+Y] = 3 * (5+7+9)/3 = 21
        self.assertAlmostEqual(state.value(var), 21.0, places=6)


class TestCase5(unittest.TestCase):
    """Basic mean."""
    def setUp(self):
        pp.reset()

    def test_mean(self):
        arr = pp.array([1, 2, 3, 4, 5, 6])
        mean = accum(each(arr)) / len(arr)
        compiled = pp.compile(mean)
        for state in compiled.run(interval=0):
            pass
        self.assertAlmostEqual(state.value(mean), 3.5, places=6)


if __name__ == '__main__':
    unittest.main()
