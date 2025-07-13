import unittest
import pyprogressive as pp
from pyprogressive import accum, each

class TestEmptyArray(unittest.TestCase):
    """빈 배열에 대한 테스트 케이스입니다."""
    def test_empty_array(self):
        # 빈 배열을 선언
        X = pp.array([])
        Y = pp.array([])
        expr = accum(each(X) + each(Y))
        prog = pp.compile(expr)

        results = []
        # callback으로 받은 값을 results에 담음
        prog.run(callback=results.append)


if __name__ == "__main__":
    unittest.main()