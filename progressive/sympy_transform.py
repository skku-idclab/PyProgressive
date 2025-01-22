# sympy_transform.py

import sympy
from sympy import sympify, expand

# expression.py 안에 있는 클래스들 import
from .expression import (
    Node, BinaryOperationNode, Addition, Subtraction,
    Multiplication, Division, PowerN,
    InplaceOperationNode, InplaceAddition, InplaceSubtraction, 
    InplaceMultiplication, InplaceDivision
)
# Variable, DataItemToken 등도 import
from .variable import Variable
from .token import DataItemToken


token_map = {}

def node_to_string(node):
    """
    Convert our Node (including Inplace nodes) into a string
    that sympy can parse.
    """
    # 1) 기본 타입(int, float)
    if isinstance(node, int):
        return str(node)
    if isinstance(node, float):
        return str(node)

    # 2) Token or Variable?
    if isinstance(node, DataItemToken):
        #symbol_name = f"arr_{id(node.array)}"
        symbol_name = "arr_i"
        token_map[symbol_name] = node.array
        return symbol_name  # 예: array[i] -> arr_1244313 (단순 가정)
    if isinstance(node, Variable):
        # Variable 내부의 expr를 문자열로 변환
        return f"({node_to_string(node.expr)})"

    # 3) BinaryOperationNode (Addition, Subtraction, ...)
    if isinstance(node, BinaryOperationNode):
        left_str = node_to_string(node.left)
        right_str = node_to_string(node.right)
        if isinstance(node, Addition):
            return f"({left_str} + {right_str})"
        elif isinstance(node, Subtraction):
            return f"({left_str} - {right_str})"
        elif isinstance(node, Multiplication):
            return f"({left_str} * {right_str})"
        elif isinstance(node, Division):
            return f"({left_str} / {right_str})"

    # 4) InplaceOperationNode (InplaceAddition, etc.)
    if isinstance(node, InplaceOperationNode):
        left_str = node_to_string(node.left)
        right_str = node_to_string(node.right)
        # Sympy에는 in-place 개념이 없으므로 일반 연산처럼 처리
        if isinstance(node, InplaceAddition):
            return f"({left_str} + {right_str})"
        elif isinstance(node, InplaceSubtraction):
            return f"({left_str} - {right_str})"
        elif isinstance(node, InplaceMultiplication):
            return f"({left_str} * {right_str})"
        elif isinstance(node, InplaceDivision):
            return f"({left_str} / {right_str})"

    # 5) PowerN
    if isinstance(node, PowerN):
        base_str = node_to_string(node.base)
        exp_str = node_to_string(node.exponent)
        return f"({base_str} ** {exp_str})"

    # 혹은 Node.__init__(expr)를 활용하는 경우,
    # node.expr를 문자열 변환해서 반환가능
    # 하지만 BinaryOperationNode 등은 이미 left/right를 쓰므로 생략.

    raise TypeError(f"Unsupported node type in node_to_string: {type(node)}")


def sympy_to_node(expr):
    """
    Convert Sympy expression back to our Node structure.
    Inplace 노드는 일반 Add/Sub와 동일하게 복원할 수 있음
    (in-place 개념을 다시 살려야 함)
    """
    if isinstance(expr, sympy.Symbol):
        name = str(expr)
        if name.startswith("arr_"):
            if name in token_map:
                print("token_map[name]: ", token_map[name].data)
                return DataItemToken(token_map[name])
            return DataItemToken()
        # 그외는 임시로 Variable(None, 0) 등으로 처리. 추후 수정 필요
        return Variable(None, 0)

    if isinstance(expr, sympy.Integer):
        return int(expr)
    if isinstance(expr, sympy.Float):
        return float(expr)

    if isinstance(expr, sympy.Add):
        args = expr.args
        if len(args) == 1:
            return sympy_to_node(args[0])
        current = sympy_to_node(args[0])
        for subexpr in args[1:]:
            current = Addition(current, sympy_to_node(subexpr))
        return current

    if isinstance(expr, sympy.Mul):
        args = expr.args
        if len(args) == 1:
            return sympy_to_node(args[0])
        current = sympy_to_node(args[0])
        for subexpr in args[1:]:
            current = Multiplication(current, sympy_to_node(subexpr))
        return current

    if isinstance(expr, sympy.Pow):
        base, exponent = expr.args
        base_node = sympy_to_node(base)
        exp_node = sympy_to_node(exponent)
        return PowerN(base_node, exp_node)

    # Division, Subtraction을 Add/Mul로 표현하는 Sympy 내부 구조에 따라,
    # (a-b) => Add(a, -b), (a/b) => Mul(a, b^-1)

    if isinstance(expr, sympy.Rational):
        return Division(sympy_to_node(expr.p), sympy_to_node(expr.q))
    
    if isinstance(expr, int):
        return expr

    raise TypeError(f"Unsupported sympy expr type: {type(expr)} => {expr}")


def flatten_with_sympy(root_node):
    """
    1) Node -> 문자열
    2) 문자열 -> sympy.sympify
    3) sympy.expand
    4) sympy -> Node
    """
    expr_str = node_to_string(root_node)
    print(f"node to string result: {expr_str}")
    sym_expr = sympify(expr_str)
    expanded_expr = expand(sym_expr)
    print(f"expanded expr: {expanded_expr}")
    return sympy_to_node(expanded_expr)
