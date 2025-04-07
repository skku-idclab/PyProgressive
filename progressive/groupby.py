from .expression import Node, GroupBy, InplaceOperationNode, BinaryOperationNode, BQ

def group_by_converter(expr, global_BQ_dict):
    if isinstance(expr, GroupBy):
        group_index = expr.group_index
        expr = expr.expr
        
        if isinstance(expr, InplaceOperationNode):
            expr = InplaceOperationNode(expr.left, expr.right, expr.in_loop)
        
        if isinstance(expr, BinaryOperationNode):
            expr = BinaryOperationNode(expr.left, expr.right)
        
        if isinstance(expr, BQ):
            expr = BQ(expr.k, expr.arridx, expr.name)
        
        return GroupBy(group_index, expr)
    else:
        raise ValueError("Invalid expression for group_by_converter")