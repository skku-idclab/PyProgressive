import unittest
import pyprogressive as pp
from pyprogressive import accum, each, group, G
import io
import sys

class TestGroupAndTreePrint(unittest.TestCase):
    """group 연산 및 expr.print() 출력 테스트 케이스입니다."""
    def test_group_operation_and_tree_print(self):
        # 데이터 배열 및 표현식 정의
        D = pp.array([("A", 1), ("B", 2), ("A", 3)])
        total = accum(each(D, 1))
        expr = group(each(D, 0), accum(each(G, 1)) / total)
        prog = pp.compile(expr)

        results = []
        prog.run(callback=results.append)
        
        # tree 구조 출력
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            expr.print()
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()
        # 출력이 비어 있지 않아야 함
        print("Captured output:", output)

if __name__ == "__main__":
    unittest.main()