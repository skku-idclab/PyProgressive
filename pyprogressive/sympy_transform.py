# sympy_transform.py

import sympy
from sympy import sympify, simplify, Symbol, expand


from .expression import (
    Node, BinaryOperationNode, Addition, Subtraction,
    Multiplication, Division, PowerN,
    InplaceOperationNode, InplaceAddition, InplaceSubtraction, 
    InplaceMultiplication, InplaceDivision, BQ, GroupBy, GBQ
)
from .variable import Variable
from .token import DataItemToken, DataLengthToken, GToken
from .array import global_arraylist

token_map = {}
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


        symbol_name = "arr_" + str(node.id)

        token_map[symbol_name] = node
        return symbol_name  # ex: array[i] -> arr_123
    
    
    if isinstance(node, DataLengthToken):
        symbol_name = f"DataLength_{node.arrayid}"
        token_map[symbol_name] = {'type': 'DataLengthToken', 'arrayid': node.arrayid}
        return symbol_name

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

    # 4) PowerN
    if isinstance(node, PowerN):
        base_str = node_to_string(node.base)
        exp_str = node_to_string(node.exponent)
        return f"({base_str} ** {exp_str})"

    # 5) BQ
    if isinstance(node, BQ):
        return node.name
    
    if isinstance(node, GBQ):
        return node.name
    
    # 6) GroupBy
    # GroupBy is a special case, we need to handle it separately
    if isinstance(node, GroupBy):
        group_index_str = node_to_string(node.group_index)
        expr_str = node_to_string(node.expr)
        array_index = node.array_index
        return f"GroupBy({group_index_str}, {array_index}, {expr_str})"
    
    if isinstance(node, GToken):
        return "arr_GToken"
    
    


    raise TypeError(f"Unsupported node type in node_to_string: {type(node)}")


def sympy_to_node(expr):
    """
    Convert Sympy expression back to our Node structure.
    Inplace can be modified to simple Add/Sub again.
    """
    if isinstance(expr, sympy.Symbol):
        name = str(expr)
        if name.startswith("arr_"):
            if name in token_map:
                return token_map[name]
            return DataItemToken()
        
        if name.startswith("BQ_"):
            bqnum = name.split("_")[1]
            if name.startswith("BQ_special"):
                bqarridx = name.split("_")[2]
            else:
                bqarridx = name.split("_")[3]
            return BQ(bqnum, bqarridx, name)
        
        if name.startswith("GroupBy_"):
            group_index = name.split("_")[1]
            expr = name.split("_")[2]
            expr = sympy_to_node(expr)
            return GroupBy(group_index, 0, expr)
        
        if name.startswith("DataLength_"):
            try:
                arrayid = int(name.split("_")[1])
                found_array = next((a for a in global_arraylist if a.id == arrayid), None)
                length_val = len(found_array.data) if found_array else None
                if length_val is None:
                     print(f"Warning: Could not find array with ID {arrayid} during sympy_to_node conversion., this is in sympy_transform.py")
                return DataLengthToken(arrayid=arrayid, value=length_val)
            except (IndexError, ValueError):
                print(f"Warning: Could not parse arrayid from symbol name: {name}, this is in sympy_transform.py")
                return DataLengthToken(arrayid=-1) 
        
        if name.startswith("GToken"):
            return GToken(access_index = name.split("_")[1])
        
        print("Warning: Unrecognized symbol name:", name)
        print("in sympytonode")

        return Variable(None, 0)
    
    if isinstance(expr, sympy.Function):
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

    sym_expr = sympify(expr_str)
    expanded_expr = expand(sym_expr)

    new_root_node = sympy_to_node(expanded_expr)

    return new_root_node


