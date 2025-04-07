from .expression import Node, GroupBy, InplaceOperationNode, BinaryOperationNode, BQ
from .array import Array, global_arraylist
def group_by_evaluator(expr, BQ_dict, idx):
    if isinstance(expr, GroupBy):
        group_index = expr.group_index
        array_index = expr.array_index
        array = global_arraylist[array_index]
        whole_length = len(array)
        item = array.data[idx]
        BQ_str_length = "BQ_group_"+str(item[group_index])+"_length_of_"+str(array_index)
        BQ_str_eval = "BQ_group_"+str(item[group_index])+"_" +"expr"+ "_of_"+str(array_index)

        if BQ_str_length not in BQ_dict:
            BQ_dict[BQ_str_length] = 1/whole_length
        else:
            BQ_dict[BQ_str_length] += 1/whole_length
        if not isinstance(item, tuple):
            raise ValueError("Array item must be a tuple in group operation")
        
        

        if isinstance(expr, BQ):
            expr = BQ(expr.k, expr.arridx, expr.name)
        
        return GroupBy(group_index, array_index, expr), BQ_dict
    else:
        raise ValueError("Invalid expression for group_by_converter")
    