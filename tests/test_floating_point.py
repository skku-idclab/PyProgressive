import unittest
import pyprogressive as pp
from pyprogressive import accum, each

class TestFloatingPointFinal(unittest.TestCase):
    """부동소수점 계산을 검증하는 테스트 케이스입니다."""
    def test_floating_point_final_value(self):
        N = 5
        X = pp.array([0.1 * i for i in range(N)])
        Y = pp.array([0.2 * i for i in range(N)])
        X1 = [0.1 * i for i in range(N)]
        Y1 = [0.2 * i for i in range(N)]

        exprf = accum(each(X) + each(Y))
        progf = pp.compile(exprf)

        # 결과값 저장
        results = []
        progf.run(callback=results.append)

        # 기대값을 값을 업데이트
        expected = 0.0
        for i in range(N):
            expected += X1[i] + Y1[i]

        self.assertEqual(len(results), 1, f"results 길이가 {len(results)}개입니다. 하나여야 합니다.")
        # 최종 값 비교 (허용 오차 1e-9)
        self.assertTrue(
            abs(results[0] - expected) < 1e-9,
            f"최종 부동소수점 값 불일치: 실제 {results[0]}, 기대 {expected}"
        )

if __name__ == "__main__":
    unittest.main()
