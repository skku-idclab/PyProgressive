# bq_converter.py

import sympy
from sympy import sympify, simplify, Symbol, expand, Poly, Function
from .sympy_transform import node_to_string, token_map
from .expression import (
    Constantized, Node, BinaryOperationNode, Addition, Subtraction,
    Multiplication, Division, PowerN,
    InplaceOperationNode, InplaceAddition, InplaceSubtraction, 
    InplaceMultiplication, InplaceDivision, BQ
)
from .variable import Variable
from .token import DataItemToken

# 사용자정의 sympy 함수: constantized 노드를 표현하기 위한 함수
class ConstantizedFunction(Function):
    @classmethod
    def eval(cls, var_name, inner_expr):
        # eval 단계에서는 바로 평가하지 않고, 보존하도록 한다.
        return None

constantized_map = {}


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

    constantized_flag = False


    if isinstance(root_node, Constantized):
        print("root_node is Constantized")
        tem = root_node
        root_node = root_node.expr
        constantized_flag = True
    # 1. Node → 문자열 → sympy 식
    expr_str = node_to_string(root_node)
    print("expr_str:", expr_str)
    try:
        sym_expr = sympify(expr_str, locals={"Constantized": ConstantizedFunction})
    except Exception as e:
        raise ValueError(f"sympify 실패: {expr_str}") from e
    

    

    # 2. 먼저, 내부에 ConstantizedFunction이 있으면 재귀적으로 처리한다.
    def replace_constantized_func(expr):
        # expr가 ConstantizedFunction인 경우
        if expr.func == ConstantizedFunction:
            # expr.args = (var_name, inner_expr)
            var_name = expr.args[0]
            inner_expr = expr.args[1]
            # 재귀 변환: inner_expr가 이미 sympy 식이므로, 
            # 이 식을 우리가 변환하는 방식(다항식 치환)으로 처리한다.
            converted_inner = convert_with_bq_from_sympy(inner_expr, array_length)
            # 내부 변환 결과에 array_length를 곱해준다.
            return converted_inner * array_length
        return expr

    sym_expr = sym_expr.replace(lambda expr: expr.func == ConstantizedFunction, replace_constantized_func)
    # 3. 전개(expand)
    sym_expr = expand(sym_expr)
    #print("expand sym_expr Result:", sym_expr)


    # 4. DataItemToken 치환: flatten 단계에서 "arr_i"로 표현된 항목을 다항식으로 보고 치환한다.
    arr_i = Symbol("arr_i")
    sym_expr = sym_expr.replace(
    lambda expr: expr.is_Pow and expr.base == arr_i and expr.exp.is_Integer,
    lambda expr: Symbol(f"BQ_{int(expr.exp)}")
    ).replace(
    lambda expr: expr == arr_i,
    lambda expr: Symbol("BQ_1")
    )

    
    #print("DataItemToken replace Result:", sym_expr)
    
    converted_sym_expr = simplify(sym_expr)

    print("convert Result:", converted_sym_expr)
    
    # 5. 최종 sympy 식을 our Node 구조로 복원하여 반환한다.
    converted_node = sympy_to_BQ_node(converted_sym_expr)

    bq_symbols = [s for s in sym_expr.atoms(Symbol) if s.name.startswith("BQ_")]
    if len(bq_symbols) != 0:
        bq_max_x = max(int(s.name.split("_")[1]) for s in bq_symbols)
        converted_node.bq_max = bq_max_x
    elif hasattr(converted_node, "bq_max"):
        converted_node.bq_max = 0

    if constantized_flag:
        label = f"Constantized_var{tem.id}"
        constantized_map[label] = converted_node

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



def sympy_to_BQ_node(expr):
    """
    Convert Sympy expression back to our Node structure.
    Inplace 노드는 일반 Add/Sub와 동일하게 복원할 수 있음
    (in-place 개념을 다시 살려야 함)
    """
    if isinstance(expr, sympy.Symbol):
        name = str(expr)
        if name.startswith("Constantized_var"):
            inner_expr = constantized_map[name]
            if inner_expr is None:
                raise ValueError(f"Constantized node '{name}' has no inner expression")
            else:
                return inner_expr
        if name.startswith("arr_"):
            if name in token_map:
                return DataItemToken(token_map[name])
            return DataItemToken()
        
        if name.startswith("BQ_"):
            bqnum = name.split("_")[1]
            return BQ(bqnum)

        # 그외는 임시로 Variable(None, 0) 등으로 처리. 추후 수정 필요
        return Variable(None, 0)

    if isinstance(expr, sympy.Integer):
        return int(expr)
    if isinstance(expr, sympy.Float):
        return float(expr)

    if isinstance(expr, sympy.Add):
        args = expr.args
        if len(args) == 1:
            return sympy_to_BQ_node(args[0])
        current = sympy_to_BQ_node(args[0])
        for subexpr in args[1:]:
            current = Addition(current, sympy_to_BQ_node(subexpr))
        return current

    if isinstance(expr, sympy.Mul):
        args = expr.args
        if len(args) == 1:
            return sympy_to_BQ_node(args[0])
        current = sympy_to_BQ_node(args[0])
        for subexpr in args[1:]:
            current = Multiplication(current, sympy_to_BQ_node(subexpr))
        return current

    if isinstance(expr, sympy.Pow):
        base, exponent = expr.args
        base_node = sympy_to_BQ_node(base)
        exp_node = sympy_to_BQ_node(exponent)
        return PowerN(base_node, exp_node)

    # Division, Subtraction을 Add/Mul로 표현하는 Sympy 내부 구조에 따라,
    # (a-b) => Add(a, -b), (a/b) => Mul(a, b^-1)

    if isinstance(expr, sympy.Rational):
        return Division(sympy_to_BQ_node(expr.p), sympy_to_BQ_node(expr.q))
    
    if isinstance(expr, int):
        return expr

    raise TypeError(f"Unsupported sympy expr type: {type(expr)} => {expr}")

