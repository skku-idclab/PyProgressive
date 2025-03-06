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


def convert_with_bq(root_node, BQ_dict):
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
    # print("root_node:")
    # root_node.print()
    
    # 1. Convert Node → string → sympy expression
    expr_str = node_to_string(root_node)
    # print("expr_str:", expr_str)
    try:
        sym_expr = sympify(expr_str, locals={"Constantized": ConstantizedFunction})
    except Exception as e:
        raise ValueError(f"sympify failed: {expr_str}") from e

    
    
    # 3. Expand the expression
    sym_expr = expand(sym_expr)
    print("expand sym_expr Result:", sym_expr)

    # 4. DataItemToken replacement: in the flatten phase, items expressed as "arr_i" are treated as a polynomial term.
    # Need to fix if we support multiple arrays.
  
    #print("before convert:", sym_expr)
    new_sym_expr = transform_expr(sym_expr)
    # print("new_sym_expr:", new_sym_expr)
    # sym_expr = sym_expr.replace(
    #     lambda expr: expr.is_Pow and expr.base.name.startswith("arr_") and expr.exp.is_Integer,
    #     lambda expr: Symbol(f"BQ_{int(expr.exp)}_of_{expr.base.name.split('_')[1]}")
    # ).replace(
    #     lambda expr: type(expr) == Symbol and expr.name.startswith("arr_"),
    #     lambda expr: Symbol("BQ_1_of_" + expr.name.split('_')[1])
    # )
    

    # print("DataItemToken replace Result:", sym_expr)

    converted_sym_expr = simplify(new_sym_expr)

    #print("convert Result:", converted_sym_expr)

    # 5. Finally, convert the resulting sympy expression back to our Node structure and return it
    converted_node = sympy_to_BQ_node(converted_sym_expr)

    bq_symbols = [s for s in new_sym_expr.atoms(Symbol) if s.name.startswith("BQ_")]
    for s in bq_symbols:
        BQ_dict[s.name] = 0
    # if len(bq_symbols) != 0:
    #     bq_max_x = max(int(s.name.split("_")[1]) for s in bq_symbols)
    #     converted_node.bq_max = bq_max_x
    # elif hasattr(converted_node, "bq_max"):
    #     converted_node.bq_max = 0

    # print("BQ_dict:", BQ_dict)
    converted_node.print()

    if constantized_flag:
        label = f"Constantized_var{tem.id}"
        constantized_map[label] = converted_node

    return converted_node, BQ_dict


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
            return BQ(bqnum, bqarridx, name)

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

import re
from sympy import Symbol, Pow, Mul
from sympy.core.expr import Expr

def extract_arr_info(expr: Expr):
    """
    If expr is of the form constant * arr_{number} or constant * (arr_{number}**exponent)
    where there is exactly one non-constant factor matching arr_{number} (or its power),
    return (number, exponent). Otherwise, return (None, None).
    """
    # Factor out constant from a multiplication.
    if expr.is_Mul:
        coeff, rest = expr.as_coeff_Mul()
        # If there are multiple non-constant factors, fail.
        if rest.is_Mul:
            return None, None
        else:
            return extract_arr_info(rest)
    # Handle power expression: arr_{number}**exponent
    if expr.is_Pow:
        base, exponent = expr.as_base_exp()
        if hasattr(base, 'name'):
            match = re.fullmatch(r'arr_(\d+)', base.name)
        else:
            return None, None
        if match and exponent.is_Integer:
            return match.group(1), exponent  # e.g., ('1', 2)
        return None, None
    # Handle simple symbol: arr_{number}
    if expr.is_Symbol:
        match = re.fullmatch(r'arr_(\d+)', expr.name)
        if match:
            # No exponent specified: we'll treat it as exponent 1 later in division/multiplication
            return match.group(1), None
    return None, None

def transform_expr(expr: Expr) -> Expr:
    # Process addition by transforming each term separately.
    if expr.is_Add:
        new_args = [transform_expr(arg) for arg in expr.args]
        return expr.func(*new_args)
    
    # Process multiplication.
    if expr.is_Mul:
        # First, check for a division pattern using as_numer_denom.
        numer, denom = expr.as_numer_denom()
        # Only apply division rule if neither numerator nor denominator is an addition.
        if denom != 1 and not (numer.is_Add or denom.is_Add):
            num_symbol, num_exp = extract_arr_info(numer)
            den_symbol, den_exp = extract_arr_info(denom)
            if num_symbol and den_symbol:
                numer_coeff, _ = numer.as_coeff_Mul()
                denom_coeff, _ = denom.as_coeff_Mul()
                const_factor = numer_coeff / denom_coeff
                # If exponent is missing, treat it as 1.
                num_exp = num_exp if num_exp is not None else 1
                den_exp = den_exp if den_exp is not None else 1
                # Always include the "pow" part.
                num_str = f"{num_symbol}_pow_{num_exp}"
                den_str = f"{den_symbol}_pow_{den_exp}"
                return Mul(1/10, const_factor * Symbol(f'BQ_special_{num_str}_div_{den_str}'))
        
        # If not a pure division, try to detect a two-factor multiplication.
        coeff, rest = expr.as_coeff_Mul()
        factors = list(rest.args) if rest.is_Mul else [rest]
        if len(factors) == 2:
            info1 = extract_arr_info(factors[0])
            info2 = extract_arr_info(factors[1])
            if info1[0] is not None and info2[0] is not None:
                exp1 = info1[1] if info1[1] is not None else 1
                exp2 = info2[1] if info2[1] is not None else 1
                a_str = f"{info1[0]}_pow_{exp1}"
                b_str = f"{info2[0]}_pow_{exp2}"
                return Mul(1/10, coeff * Symbol(f'BQ_special_{a_str}_mul_{b_str}'))
        # Otherwise, recursively process each factor.
        new_args = [transform_expr(arg) for arg in expr.args]
        return Mul(*new_args)
    
    # Process power expressions: if the base is of the form arr_{number},
    # convert arr_i**k to BQ_k_of_i (using the normal rule).
    if expr.is_Pow:
        base, exponent = expr.as_base_exp()
        if base.is_Symbol:
            match = re.fullmatch(r'arr_(\d+)', base.name)
            if match and exponent.is_Integer:
                exp_val = exponent if exponent is not None else 1
                return Mul(1/10 ,Symbol(f'BQ_{exp_val}_of_{match.group(1)}'))
        new_base = transform_expr(base)
        new_exponent = transform_expr(exponent)
        return new_base ** new_exponent

    # General symbol handling for simple symbols:
    # Keep the original rule: arr_i becomes BQ_1_of_i.
    if expr.is_Symbol:
        if expr.name.startswith("arr_"):
            match = re.fullmatch(r'arr_(\d+)', expr.name)
            if match:
                return Mul(1/10, Symbol(f'BQ_1_of_{match.group(1)}'))
    
    # Recursively process any sub-expressions.
    if expr.args:
        new_args = tuple(transform_expr(arg) for arg in expr.args)
        return expr.func(*new_args)
    
    return expr