from progressive.expression import Addition, Subtraction, Multiplication, Division, PowerN
from progressive.variable import Variable

def evaluate(node, bq_values):
    """
    Evaluates the given computation tree (node) and returns the final value.
    bq_values is a list of numeric values corresponding to each BQ symbol,
    for example [BQ_1_value, BQ_2_value, ...].

    This function traverses the tree recursively and handles each node type as follows:
      - If the node is a number (int, float), return it as is.
      - If the node is a BQ_x node, extract the index from the string (e.g., "BQ_1") and
        return the corresponding value from bq_values.
      - If the node is an operator node (Addition, Multiplication, Division, PowerN, etc.),
        recursively evaluate its children and perform the respective operation.
      - Otherwise, if the node has an attribute 'expr', evaluate that attribute.

    Parameters:
        node: The root node of the computation tree (an instance of our Node class).
        bq_values (list): A list of values in the form [BQ_1, BQ_2, ...].

    Returns:
        The final computed value.
    """
    # If it's a basic numeric type, return it directly
    if isinstance(node, (int, float)):
        return node

    # Convert to string and check if it's a BQ_x node (usually "BQ_1", "BQ_2", etc.)
    node_str = str(node)
    if node_str.startswith("BQ_"):
        bq_num = int(node_str.split("_")[1])
        return bq_values[bq_num - 1]

    # Handle operator nodes
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
    # PowerN
    elif isinstance(node, PowerN):
        return evaluate(node.base, bq_values) ** evaluate(node.exponent, bq_values)

    # If the node has an 'expr' attribute, evaluate that (e.g., Variable node)
    if hasattr(node, "expr"):
        return evaluate(node.expr, bq_values)

    # If the node provides a value() method, use it to evaluate
    if hasattr(node, "value") and callable(node.value):
        return node.value()

    # If the node type is not supported, raise an error
    raise TypeError(f"Unsupported node type: {node}")
