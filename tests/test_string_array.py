import unittest
import pyprogressive as pp

class TestBadArrayInput(unittest.TestCase):
    """비정상적인 배열 입력에 대한 테스트 케이스입니다."""
    def test_array_with_string_input(self):
        # 문자열을 입력하면 적절한 예외(TypeError 또는 ValueError)가 발생해야 합니다.
        with self.assertRaises(Exception):
            pp.array("not a list")

if __name__ == "__main__":
    unittest.main()