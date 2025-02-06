# bq_converter.py

import sympy
from sympy import sympify, simplify, Symbol, expand, Poly, Function
from .sympy_transform import node_to_string, sympy_to_node

# 사용자정의 sympy 함수: constantized 노드를 표현하기 위한 함수
class ConstantizedFunction(Function):
    @classmethod
    def eval(cls, var_name, inner_expr):
        # eval 단계에서는 바로 평가하지 않고, 보존하도록 한다.
        return None

def convert_with_bq(root_node, array_length):
    """
    평탄화 및 constantized 처리가 완료된 표현식 트리(root_node)를 받아서,
    전체 식을 데이터 토큰(arr_i)에 관한 다항식으로 보고,
    각 단항 a_k * arr_i^k를 a_k * BQ_k로 치환하는 한편,
    만약 식 내에 ConstantizedFunction("var", inner_expr)가 있다면,
    내부 표현식(inner_expr)을 재귀적으로 변환하여 그 결과를 사용한다.
    
    최종적으로, 예를 들어
       for i in loop:
           psum += array[i]
       psum /= len(array)
    의 경우, 내부에서 누적된 표현식이 최종적으로 (BQ_1 * array_length)/array_length → BQ_1
    로 전개되어야 하며, 분산 계산 등도 여러 BQ들의 조합으로 표현될 수 있어야 한다.
    
    Parameters:
        root_node (Node): 평탄화 및 constantized 처리가 완료된 표현식 트리.
        array_length (int): 배열의 길이.
        
    Returns:
        Node: 변환된, BQ 전개가 적용된 표현식 트리.
    """
    # 1. Node → 문자열 → sympy 식
    expr_str = node_to_string(root_node)
    print("expr_str:", expr_str)
    try:
        sym_expr = sympify(expr_str, locals={"Constantized": ConstantizedFunction})
    except Exception as e:
        raise ValueError(f"sympify 실패: {expr_str}") from e


    # 4. DataItemToken 치환: flatten 단계에서 "arr_i"로 표현된 항목을 다항식으로 보고 치환한다.
    arr_i = Symbol("arr_i")
    sym_expr = sym_expr.replace(
        lambda expr: expr == arr_i or (expr.is_Pow and expr.base == arr_i and expr.exp.is_Integer),
        lambda expr: Symbol("BQ_1") if expr == arr_i else Symbol(f"BQ_{int(expr.exp)}")
    )
    
    # 5. sym_expr를 arr_i에 관한 다항식으로 본다.
    poly = sym_expr.as_poly(arr_i)
    if poly is None:
        converted_sym_expr = simplify(sym_expr)
    else:
        new_expr = 0
        # poly.as_dict()는 각 단항 (exponent 튜플)와 계수를 담은 딕셔너리를 반환한다.
        for monom, coeff in poly.as_dict().items():
            k = monom[0]  # arr_i의 차수
            # 각 단항 a_k * arr_i^k를 a_k * BQ_k로 대체
            new_expr += coeff * Symbol("BQ_" + str(k))
        converted_sym_expr = simplify(new_expr)

    print("convert Result:", converted_sym_expr)
    
    # 6. 최종 sympy 식을 our Node 구조로 복원하여 반환한다. -> 이 부분이 문제다. BQ를 제대로 노드로 변환을 못함.
    converted_node = sympy_to_node(converted_sym_expr)
    return converted_node

def convert_with_bq_from_sympy(sym_expr, array_length):
    """
    sym_expr (sympy 표현식)을 받아서, arr_i에 관한 다항식 치환을 수행하는
    함수. convert_with_bq 함수의 내부에서 사용된다.
    """
    sym_expr = expand(sym_expr)
    arr_i = Symbol("arr_i")
    poly = sym_expr.as_poly(arr_i)
    if poly is None:
        return simplify(sym_expr)
    else:
        new_expr = 0
        for monom, coeff in poly.as_dict().items():
            k = monom[0]
            new_expr += coeff * Symbol("BQ_" + str(k))
        return simplify(new_expr)
