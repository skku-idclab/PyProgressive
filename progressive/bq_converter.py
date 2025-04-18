# bq_converter.py

import sympy
from sympy import sympify, simplify, Symbol, expand, Poly, Function, Mul, Pow
from sympy.core.expr import Expr
from .sympy_transform import node_to_string, token_map
from .expression import (
    Node, BinaryOperationNode, Addition, Subtraction,
    Multiplication, Division, PowerN, BQ, GroupBy
)
from .variable import Variable
from .token import DataItemToken, DataLengthToken, GToken
from .array import global_arraylist

import re


def convert_with_bq(root_node, BQ_dict):
    """
    Takes a flattened and constantized expression tree (root_node) and interprets the entire expression
    as a polynomial in terms of the data token (arr_i). Each term a_k * arr_i^k is replaced with a_k * BQ_k.
    
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
    
    # 1. Convert Node → string → sympy expression
    expr_str = node_to_string(root_node)
    try:
        sym_expr = sympify(expr_str)
    except Exception as e:
        raise ValueError(f"sympify failed: {expr_str}") from e

    
    
    # 2. Expand the expression
    sym_expr = expand(sym_expr)


    # 3. DataItemToken replacement: in the flatten phase, items expressed as "arr_i" are treated as a polynomial term.
    # print("=== Before Transform ===")
    # print(sym_expr)
    new_sym_expr = transform_expr(sym_expr)

    converted_sym_expr = simplify(new_sym_expr)
    
    # print("=== After Transform ===")
    # print(new_sym_expr)

    # 4. Finally, convert the resulting sympy expression back to our Node structure and return it
    converted_node = sympy_to_BQ_node(converted_sym_expr)

    bq_symbols = [s for s in new_sym_expr.atoms(Symbol) if s.name.startswith("BQ_")]
    for s in bq_symbols:
        BQ_dict[s.name] = 0


    return converted_node, BQ_dict


def sympy_to_BQ_node(expr):
    """
    Convert a Sympy expression back to our Node structure.
    In-place nodes can be restored the same way as normal Add/Sub
    (we would need to reintroduce the in-place concept if necessary).
    """
    if isinstance(expr, sympy.Symbol):
        name = str(expr)
        if name.startswith("arr_"):
            if name in token_map:
                return token_map[name]
            return DataItemToken()
        
        if name.startswith("BQ_"):
            if name.startswith("BQ_special"):
                bqnum = name.split("_")[4]
                bqarridx = name.split("_")[2]
            else:
                bqnum = name.split("_")[1]
                bqarridx = name.split("_")[3]
            return BQ(bqnum, bqarridx, name)
        
        # if name.startswith("DataLength"):
        #     # DataLengthToken is handled in the sympy_to_node function
        #     return DataLengthToken(value = len(global_arraylist[0]))

        if name.startswith("DataLength_"):
            try:
                if name.startswith("DataLength_GToken"):
                    return DataLengthToken(arrayid = "GToken", ingroup = True)
                if name.startswith("DataLength_constant"):
                    return DataLengthToken(arrayid = "constant", ingroup = True)
                arrayid = int(name.split("_")[1])
                # value는 여기서 global_arraylist 참조하여 설정하거나, None으로 두고 evaluator에서 처리
                found_array = next((a for a in global_arraylist if a.id == arrayid), None)
                length_val = len(found_array.data) if found_array else None
                if length_val is None:
                     print(f"Warning: Could not find array with ID {arrayid} during sympy_to_node conversion., this is in group_bq_converter.py")
                return DataLengthToken(arrayid=arrayid, value=length_val)
            except (IndexError, ValueError):
                print(f"Warning: Could not parse arrayid from symbol name: {name} , this is in group_bq_converter.py")
                # 오류 처리 또는 기본값 반환
                return DataLengthToken(arrayid=-1) # 예: 잘못된 ID


        if isinstance(expr, DataLengthToken):
            symbol_name = f"DataLength_{expr.arrayid}"
            # token_map에 arrayid 정보를 저장할 필요가 있을 수 있음 (복원 시 사용)
            token_map[symbol_name] = {'type': 'DataLengthToken', 'arrayid': expr.arrayid}
            return symbol_name

        if name.startswith("GToken"):
            # print("GToken detected")
            return GToken(access_index = name.split("_")[1])
        
        print("Warning: Unrecognized symbol name:", name)

        # Otherwise, temporarily handle as Variable(None, 0), needs revision later
        return Variable(None, 0)
    
    if isinstance(expr, sympy.Function):
        # Handle unknown functions as a placeholder
        name = str(expr)
        if name.startswith("GroupBy"):
            group_index = name.split("(")[1].split(",")[0]
            group_index = group_index.strip()
            group_index = int(group_index)
            array_index = name.split(",")[1]
            array_index = array_index.strip()
            expr = name.split(",")[1].split(")")[0]
            expr = expr.strip()
            return GroupBy(group_index, array_index, expr)
        raise ValueError(f"Unknown function: {name}")

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
                return Mul(1, const_factor * Symbol(f'BQ_special_{num_str}_div_{den_str}'))
        
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
                return Mul(1, coeff * Symbol(f'BQ_special_{a_str}_mul_{b_str}'))
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
                return Mul(1 ,Symbol(f'BQ_{exp_val}_of_{match.group(1)}'))
        new_base = transform_expr(base)
        new_exponent = transform_expr(exponent)
        return new_base ** new_exponent

    # General symbol handling for simple symbols:
    # Keep the original rule: arr_i becomes BQ_1_of_i.
    if expr.is_Symbol:
        if expr.name.startswith("arr_"):
            match = re.fullmatch(r'arr_(\d+)', expr.name)
            if match:
                return Mul(1, Symbol(f'BQ_1_of_{match.group(1)}'))
    
    # Recursively process any sub-expressions.
    if expr.args:
        new_args = tuple(transform_expr(arg) for arg in expr.args)
        return expr.func(*new_args)
    
    return expr