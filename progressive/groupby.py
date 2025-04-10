from .expression import Node, GroupBy, InplaceOperationNode, BinaryOperationNode, BQ, Addition, Subtraction, Multiplication, Division, PowerN
from .variable import Variable
from .bq_converter import convert_with_bq
from .array import Array, global_arraylist
from .token import DataItemToken, DataLengthToken
def group_by_bq_update(expr, BQ_dict, idx):
    if isinstance(expr, GroupBy):
        group_index = expr.group_index
        array_index = expr.array_index
        array = global_arraylist[array_index]
        whole_length = len(array)
        item = array.data[idx]
        BQ_str_grouplength_rate = "BQ_grouplength_"+str(item[group_index])+"_lengthrate_of_"+str(array_index)
        BQ_str_eval = "BQ_group_"+str(item[group_index])+"_" 
        BQ_str_dict = {}
        BQ_group_dict = {}
        _, BQ_str_dict = convert_with_bq(expr.expr, BQ_str_dict)

        

        for key in BQ_str_dict.keys():
            tem = BQ_str_eval + key
            BQ_group_dict[tem] = 0
        

        if BQ_str_grouplength_rate not in BQ_dict:
            BQ_dict[BQ_str_grouplength_rate] = 1/(idx+1)
        else:
            BQ_dict[BQ_str_grouplength_rate] = (BQ_dict[BQ_str_grouplength_rate] * (idx) + 1) / (idx+1)
        
        for key in BQ_dict.keys():
            if key.startswith("BQ_grouplength") and key != BQ_str_grouplength_rate:
                BQ_dict[key] = BQ_dict[key] * (idx) / (idx+1)

        for key in BQ_group_dict.keys():
            key_str = key.split("_")
            # print("key_str: ", key_str)
            if key_str[1] == "group":
                degree, compute_arr = key_str[4], key_str[6]
                target_arr = None
                for array in global_arraylist:
                    if array.id == int(compute_arr):
                        target_arr = array
                if(target_arr == None):
                    raise ValueError("Array not found")
                if key not in BQ_dict:
                    BQ_dict[key] = item[1] ** (int(degree))
                else:
                    cateogry = key_str[2]
                    category_lengthrate = BQ_dict["BQ_grouplength_"+cateogry+"_lengthrate_of_"+str(compute_arr)]
                    category_length = category_lengthrate * (idx+1) 
                    BQ_dict[key] = (BQ_dict[key] * (category_length-1) + item[1] ** (int(degree))) / category_length # TODO: Data Item Indexing
        #print("BQ_dict: ", BQ_dict)


        if not isinstance(item, tuple):
            raise ValueError("Array item must be a tuple in group operation")
        
        
        return GroupBy(group_index, array_index, expr.expr), BQ_dict
    else:
        raise ValueError("Invalid expression for group_by_converter")

def group_evaluator(var, BQ_group_dict, category = None, index = None):
    node = var
    if isinstance(node, GroupBy):
        print("BQ_group_dict:", BQ_group_dict)
        node.print()
        categoryies = set()
        category_values = {}
        for key in BQ_group_dict.keys():
            if key.startswith("BQ_group"):
                categoryies.add(key.split("_")[2])
        # print("category:", category)
        # print("categoryies:", categoryies)
        for target_category in categoryies:
            category_values[target_category] = group_evaluator(node.expr, BQ_group_dict, category = target_category)
            category_values[target_category] = category_values[target_category]
    

        node.val = category_values
        return category_values

        pass
    # If it's a basic numeric type, return it directly
    if isinstance(node, (int, float)):
        return node
    
    if isinstance(node, DataLengthToken):
        target = "BQ_grouplength_"+str(category)+"_lengthrate_of_"+str(node.arrayid)
        # print("target:", target)
        # print("BQ_group_dict:", BQ_group_dict)
        if target not in BQ_group_dict:
            raise ValueError("Array not found")
        return BQ_group_dict[target]* len(global_arraylist[0])

    # Convert to string and check if it's a BQ_x node (usually "BQ_1", "BQ_2", etc.)
    node_str = str(node)
    if node_str.startswith("BQ_"):
        if category is None:
            raise ValueError("Category is None")
        target = "BQ_group_"+str(category)+"_"+node_str
        return BQ_group_dict[target] 

    # Handle operator nodes
    # Addition
    if isinstance(node, Addition):
        return group_evaluator(node.left, BQ_group_dict, category) + group_evaluator(node.right, BQ_group_dict, category)
    # Subtraction
    elif isinstance(node, Subtraction):
        return group_evaluator(node.left, BQ_group_dict, category) - group_evaluator(node.right, BQ_group_dict, category)
    # Multiplication
    elif isinstance(node, Multiplication):
        return group_evaluator(node.left, BQ_group_dict, category) * group_evaluator(node.right, BQ_group_dict, category)
    # Division
    elif isinstance(node, Division):
        return group_evaluator(node.left, BQ_group_dict, category) / group_evaluator(node.right, BQ_group_dict, category)
    # PowerN
    elif isinstance(node, PowerN):
        return group_evaluator(node.base, BQ_group_dict, category) ** group_evaluator(node.exponent, BQ_group_dict, category)
    
    # if isinstance(node, Variable):
    #     if node.value() == None:
    #         return group_evaluator(node.expr, BQ_group_dict, category)
    #     else:
    #         return node.value()
    # If the node has an 'expr' attribute, evaluate that (e.g., Variable node)
    if hasattr(node, "expr"):
        return group_evaluator(node.expr, BQ_group_dict, category)

    # If the node provides a value() method, use it to evaluate
    if hasattr(node, "value") and callable(node.value):
        return node.value()
    

    # If the node type is not supported, raise an error
    raise TypeError(f"Unsupported node type: {node}")
    pass