# sympy_transform.py

import sympy
from sympy import sympify, simplify, Symbol, expand


# expression.py 안에 있는 클래스들 import
from .expression import (
    Constantized, Node, BinaryOperationNode, Addition, Subtraction,
    Multiplication, Division, PowerN,
    InplaceOperationNode, InplaceAddition, InplaceSubtraction, 
    InplaceMultiplication, InplaceDivision, BQ
)
# Variable, DataItemToken 등도 import
from .variable import Variable
from .token import DataItemToken


token_map = {}
constantized_map = {}
def node_to_string(node):
    """
    Convert our Node (including Inplace nodes) into a string
    that sympy can parse.
    """
    # 1) base type(int, float)
    if isinstance(node, int):
        return str(node)
    if isinstance(node, float):
        return str(node)

    # 2) Token or Variable?
    if isinstance(node, DataItemToken):
        #symbol_name = f"arr_{id(node.array)}"
        symbol_name = "arr_" + str(node.id)
        token_map[symbol_name] = node
        return symbol_name  # ex: array[i] -> arr_123
    if isinstance(node, Variable):
        # Convert expr (in Variable) to string
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
        # No in-place scheme in Sympy, simply convert to normal operation
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

    # 6) Constantized 
    if isinstance(node, Constantized):
        # TODO: handle Constantized node 
        label = f"Constantized_var{node.id}"
        constantized_map[label] = node
        expr_str = node_to_string(node.expr)
        return label


    # 7) BQ
    if isinstance(node, BQ):
        return node.name
    


    raise TypeError(f"Unsupported node type in node_to_string: {type(node)}")


def sympy_to_node(expr):
    """
    Convert Sympy expression back to our Node structure.
    Inplace can be modified to simple Add/Sub again.
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
                return token_map[name]
            return DataItemToken()
        
        if name.startswith("BQ_"):
            bqnum = name.split("_")[1]
            bqarridx = name.split("_")[2]
            return BQ(bqnum, bqarridx)

        # others considered as Variable(None, 0). will be modified later
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

    # Division, Subtraction -> Addition, Multiplation in Sympy, 
    # (a-b) => Add(a, -b), (a/b) => Mul(a, b^-1)

    if isinstance(expr, sympy.Rational):
        return Division(sympy_to_node(expr.p), sympy_to_node(expr.q))
    
    if isinstance(expr, int):
        return expr

    raise TypeError(f"Unsupported sympy expr type: {type(expr)} => {expr}")


def flatten_with_sympy(root_node):
    """
    1) Node -> string
    2) string -> sympy.sympify
    3) sympy.expand
    4) sympy -> Node
    """
    expr_str = node_to_string(root_node)
    # print(f"node to string result: {expr_str}")
    sym_expr = sympify(expr_str)
    expanded_expr = expand(sym_expr)
    # print(f"expanded expr: {expanded_expr}")
    new_root_node = sympy_to_node(expanded_expr)
    #print("=== After Flatten with Sympy ===")
    #new_root_node.print()
    return new_root_node


