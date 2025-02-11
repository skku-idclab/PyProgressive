from progressive.expression import Addition, Subtraction, Multiplication, Division, PowerN
from progressive.variable import Variable

def evaluate(node, bq_values):
    """
    주어진 computation tree (node)를 평가하여 최종 값을 반환한다.
    bq_values는 {"BQ_1": value1, "BQ_2": value2, ...}와 같이,
    각 BQ 심볼에 대응하는 실제 숫자 값을 담은 딕셔너리이다.

    이 함수는 재귀적으로 트리를 순회하며, 각 노드의 타입에 따라 다음과 같이 처리한다:
      - 숫자 (int, float)인 경우: 그대로 반환.
      - BQ_x 노드인 경우: 노드의 문자열 표현(예: "BQ_1")을 확인하여, bq_values에서 대체값을 반환.
      - 연산자 노드(Addition, Multiplication, Division, PowerN 등)인 경우: 자식 노드를 재귀적으로 평가한 후
        해당 연산을 수행.
      - 그 외에, 만약 노드에 'expr'라는 속성이 있다면, 그 속성을 평가.

    Parameters:
        node: 평가할 트리의 루트 노드 (our Node 인스턴스).
        bq_values (list)): [BQ_1, BQ_2, ...] 형태의 리스트.

    Returns:
        계산된 최종 값.
    """
    # 기본 숫자형이면 그대로 반환
    if isinstance(node, (int, float)):
        return node

    # 문자열로 변환하여 BQ_x 노드 여부 확인 (BQ 노드는 보통 "BQ_1", "BQ_2", … 형태)
    node_str = str(node)
    if node_str.startswith("BQ_"):
        bq_num = int(node_str.split("_")[1])
        return bq_values[bq_num-1]

    # 연산자 노드 처리
    # Addition
    if isinstance(node, Addition):
        return evaluate(node.left, bq_values) + evaluate(node.right, bq_values)
    # Subtraction
    elif isinstance(node, Subtraction):
        return evaluate(node.left, bq_values) - evaluate(node.right, bq_values)
    # Multiplication
    elif isinstance(node, Multiplication):
        return evaluate(node.left, bq_values) * evaluate(node.right, bq_values)
    # Division
    elif isinstance(node, Division):
        return evaluate(node.left, bq_values) / evaluate(node.right, bq_values)
    # PowerN (거듭제곱)
    elif isinstance(node, PowerN):
        return evaluate(node.base, bq_values) ** evaluate(node.exponent, bq_values)

    # 만약 노드가 'expr' 속성을 가지고 있으면, 해당 expr를 평가 (예: Variable 노드)
    if hasattr(node, "expr"):
        return evaluate(node.expr, bq_values)

    # 만약 노드가 value() 메서드를 제공하면, 이를 이용하여 값을 평가
    if hasattr(node, "value") and callable(node.value):
        return node.value()

    # 그 외 처리할 수 없는 노드의 경우 에러 발생
    raise TypeError(f"지원하지 않는 노드 타입: {node}")
