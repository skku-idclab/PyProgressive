import unittest
import pyprogressive as pp
from pyprogressive import accum, each

class TestArrayRecompile(unittest.TestCase):
    """길이가 다른 배열을 선언했을 때 컴파일이 잘 되는지 확인하는 테스트 케이스"""
    def test_run_on_different_lengths(self):
        # 1) 길이 6 배열로 컴파일·실행
        X1 = pp.array([1, 2, 3, 4, 5, 6])
        Y1 = pp.array([10, 20, 30, 40, 50, 60])
        expr1 = accum(each(X1) * each(Y1))
        prog1 = pp.compile(expr1)
        prog1.run(callback=lambda var: print(expr1))

        # 2) 길이 5 배열로 새로 컴파일·실행 (이전 크기와 상관 없이 동작해야 함)
        X2 = pp.array([1, 2, 3, 4, 5])
        Y2 = pp.array([10, 20, 30, 40, 50])
        expr2 = accum(each(X2) * each(Y2))
        prog2 = pp.compile(expr2)
        prog2.run(interval=0.01, callback=lambda var: print(expr2))


if __name__ == "__main__":
    unittest.main()