import unittest
import progressive as pp

class TestLoop(unittest.TestCase):
    def test_no_nested_loop(self):
        ps = pp.Session()
        array = pp.Array([1, 2, 3, 4, 5])
        with self.assertRaises(Exception):
            with ps.loop(array) as loop:
                for i in loop:
                    for j in loop:
                        pass

if __name__ == "__main__":
    unittest.main()
