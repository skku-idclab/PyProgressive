from .expression import (
    Node, Addition, Subtraction, Multiplication, Division, PowerN
)
from .variable import Variable

def flatten_add_sub(node):
    """
    Flattens nested additions and subtractions into a chain of + and -.
    For example:
        (a + (b + c))   -> (a + b + c)
        (a - (b + c))   -> (a - b - c)

    Implementation detail:
     - We collect all terms (node, sign) from the subtree,
       treating Subtraction(a, b) as a + (-1)*b.
     - Then we rebuild a left-associative expression tree:
       e.g., [n1(+), n2(+), n3(-)] => (n1 + n2) - n3

    Args:
        node (Node): The root of the expression subtree to flatten.

    Returns:
        Node: A new Node that is equivalent but with no nested Add/Sub.
    """
    terms = _collect_add_sub(node)
    if not terms:
        # If there's nothing to flatten, return the original node
        return node

    # Build the chain from left to right
    base_node, base_sign = terms[0]
    if base_sign == -1:
        zero = _make_zero_constant()
        current = Subtraction(zero, base_node)
    else:
        current = base_node

    for (subnode, sign) in terms[1:]:
        if sign == +1:
            current = Addition(current, subnode)
        else:
            current = Subtraction(current, subnode)

    return current


def _collect_add_sub(node):
    """
    Recursively collects terms from an Addition or Subtraction node,
    returning a list of (subnode, sign).

    If node = Subtraction(a, b), treat it as a + (-1 * b).
    Thus b is added with a negative sign.

    Example:
        If node = Addition(a, b),
         - a => might yield [(x1,+1), (x2,+1)]
         - b => might yield [(y1,+1), (y2,-1)]
        We combine them: [(x1,+1), (x2,+1), (y1,+1), (y2,-1)]
    """
    if isinstance(node, Addition):
        left_terms = _collect_add_sub(node.left)
        right_terms = _collect_add_sub(node.right)
        return left_terms + right_terms

    elif isinstance(node, Subtraction):
        left_terms = _collect_add_sub(node.left)
        right_terms = _collect_add_sub(node.right)
        # Invert the sign of the right side
        inverted_right = [(sub, -sign) for (sub, sign) in right_terms]
        return left_terms + inverted_right

    # If not Add/Sub, consider it a single term with +1 sign
    return [(node, +1)]


def _make_zero_constant():
    """
    Creates a Node that represents the constant 0.
    This could be a specialized 'Constant(0)' node, or a Variable with expr=0, etc.
    Adjust as needed for your expression system.
    """
    dummy_loop = None  # or a real loop if necessary
    zero_var = Variable(loop=dummy_loop, expr=0)
    return zero_var
