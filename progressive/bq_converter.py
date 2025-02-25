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

# User-defined sympy function: function to represent constantized nodes
class ConstantizedFunction(Function):
    @classmethod
    def eval(cls, var_name, inner_expr):
        # Do not evaluate immediately during the eval stage; preserve it.
        return None

constantized_map = {}


def convert_with_bq(root_node, array_length, BQ_dict):
    """
    Takes a flattened and constantized expression tree (root_node) and interprets the entire expression
    as a polynomial in terms of the data token (arr_i). Each term a_k * arr_i^k is replaced with a_k * BQ_k.
    Additionally, if the expression contains ConstantizedFunction("var", inner_expr), the inner expression (inner_expr) is
    recursively converted and the result is used.
    
    In the end, for example:
       for i in loop:
           psum += array[i]
       psum /= len(array)
    the internally accumulated expression should finally expand to (BQ_1 * array_length)/array_length → BQ_1,
    and other distributed calculations should also be expressed as a combination of multiple BQs.

    Parameters:
        root_node (Node): The expression tree after flattening and constantization.
        array_length (int): The length of the array.

    Returns:
        Node: The converted expression tree with BQ expansion applied.
    """

    constantized_flag = False

    if isinstance(root_node, Constantized):
        tem = root_node
        root_node = root_node.expr
        constantized_flag = True
    
    # 1. Convert Node → string → sympy expression
    expr_str = node_to_string(root_node)
    # print("expr_str:", expr_str)
    try:
        sym_expr = sympify(expr_str, locals={"Constantized": ConstantizedFunction})
    except Exception as e:
        raise ValueError(f"sympify failed: {expr_str}") from e

    # 2. If there's a ConstantizedFunction inside, process it recursively
    def replace_constantized_func(expr):
        # If expr is ConstantizedFunction
        if expr.func == ConstantizedFunction:
            # expr.args = (var_name, inner_expr)
            var_name = expr.args[0]
            inner_expr = expr.args[1]
            # Recursive conversion: inner_expr is already a sympy expression,
            # so we handle it with our polynomial replacement approach.
            converted_inner = convert_with_bq_from_sympy(inner_expr, array_length)
            # Multiply the inner conversion result by array_length.
            return converted_inner * array_length
        return expr

    sym_expr = sym_expr.replace(lambda expr: expr.func == ConstantizedFunction, replace_constantized_func)
    
    # 3. Expand the expression
    sym_expr = expand(sym_expr)
    # print("expand sym_expr Result:", sym_expr)

    # 4. DataItemToken replacement: in the flatten phase, items expressed as "arr_i" are treated as a polynomial term.
    # Need to fix if we support multiple arrays.
    arr_i = Symbol("arr_i")
    sym_expr = sym_expr.replace(
        lambda expr: expr.is_Pow and expr.base.name.startswith("arr_") and expr.exp.is_Integer,
        lambda expr: Symbol(f"BQ_{int(expr.exp)}_of_{expr.base.name.split('_')[1]}")
    ).replace(
        lambda expr: type(expr) == Symbol and expr.name.startswith("arr_"),
        lambda expr: Symbol("BQ_1_of_" + expr.name.split('_')[1])
    )

    # print("DataItemToken replace Result:", sym_expr)

    converted_sym_expr = simplify(sym_expr)

    # print("convert Result:", converted_sym_expr)

    # 5. Finally, convert the resulting sympy expression back to our Node structure and return it
    converted_node = sympy_to_BQ_node(converted_sym_expr)

    bq_symbols = [s for s in sym_expr.atoms(Symbol) if s.name.startswith("BQ_")]
    for s in bq_symbols:
        BQ_dict[s.name] = 0
    if len(bq_symbols) != 0:
        bq_max_x = max(int(s.name.split("_")[1]) for s in bq_symbols)
        converted_node.bq_max = bq_max_x
    elif hasattr(converted_node, "bq_max"):
        converted_node.bq_max = 0

    if constantized_flag:
        label = f"Constantized_var{tem.id}"
        constantized_map[label] = converted_node

    return converted_node, BQ_dict


def convert_with_bq_from_sympy(sym_expr, array_length):
    """
    Takes a sym_expr (a sympy expression), performs the polynomial replacement
    with respect to arr_i, and returns the result. Used internally by convert_with_bq.
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
    Convert a Sympy expression back to our Node structure.
    In-place nodes can be restored the same way as normal Add/Sub
    (we would need to reintroduce the in-place concept if necessary).
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
            bqarridx = name.split("_")[3]
            return BQ(bqnum, bqarridx)

        # Otherwise, temporarily handle as Variable(None, 0), needs revision later
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

    # Division and Subtraction are represented internally in Sympy as Add/Mul:
    # (a-b) => Add(a, -b), (a/b) => Mul(a, b^-1)

    if isinstance(expr, sympy.Rational):
        return Division(sympy_to_BQ_node(expr.p), sympy_to_BQ_node(expr.q))
    
    if isinstance(expr, int):
        return expr

    raise TypeError(f"Unsupported sympy expr type: {type(expr)} => {expr}")
