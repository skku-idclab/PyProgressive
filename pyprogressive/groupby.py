from .expression import Node, GroupBy, InplaceOperationNode, BinaryOperationNode, BQ, Addition, Subtraction, Multiplication, Division, PowerN
from .variable import Variable
from .group_bq_converter import group_convert_with_bq
from .array import array, global_arraylist
from .token import DataItemToken, DataLengthToken, GToken



def detect_group_bq(expr, BQ_dict, idx):
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

        _, BQ_str_dict = group_convert_with_bq(expr.expr, BQ_str_dict)


        

        for key in BQ_str_dict.keys():
            if key.startswith("GBQ"):
                num = key.split("_")[1]
                tem = BQ_str_eval + "GBQ_" + str(num) +"_of_"+str(array_index)
            else:
                tem = BQ_str_eval + key
            if tem not in BQ_dict:
                BQ_dict[tem] = 0
            

        if BQ_str_grouplength_rate not in BQ_dict:
            BQ_dict[BQ_str_grouplength_rate] = 0

        return BQ_dict


def group_by_bq_update(BQ_dict, idx):



    
    for key in BQ_dict.keys():
        key_str = key.split("_")
        if key.startswith("BQ_grouplength"):
            using_array_idx = key_str[-1]
            using_array = global_arraylist[int(using_array_idx)]
            item = using_array.data[idx]
            group_index = 0 # TODO: need to fix here for group index
            if key_str[2] == item[group_index]:
                BQ_dict[key] = (BQ_dict[key] * (idx) + 1) / (idx+1)
            else:
                BQ_dict[key] = BQ_dict[key] * (idx) / (idx+1)
    

    for key in BQ_dict.keys():


        if not key.startswith("BQ_group"):
            continue
        key_str = key.split("_")
        using_array_idx = key_str[-1]
        using_array = global_arraylist[int(using_array_idx)]
        item = using_array.data[idx]
        group_index = 0 
        if key_str[1] == "group" and key_str[2] == item[group_index]:
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


        
        
    return BQ_dict

def group_evaluator(var, BQ_group_dict, category = None, index = None, gindex = None, normal_BQ_dict = None):
    node = var
    if isinstance(node, GroupBy):

        categoryies = set()
        category_values = {}
        for key in BQ_group_dict.keys():
            if key.startswith("BQ_group"):
                categoryies.add(key.split("_")[2])

        for target_category in categoryies:
            category_values[target_category] = group_evaluator(node.expr, BQ_group_dict, category = target_category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
            category_values[target_category] = category_values[target_category]
    

        node.val = category_values
        return category_values

        pass
    # If it's a basic numeric type, return it directly
    if isinstance(node, (int, float)):
        return node
    
    if isinstance(node, DataLengthToken):
        if node.arrayid == "GToken":
            target = "BQ_grouplength_"+str(category)+"_lengthrate_of_"+str(gindex)
            return BQ_group_dict[target] * len(global_arraylist[0])
        elif node.arrayid == "constant":
            target = "BQ_grouplength_"+str(category)+"_lengthrate_of_"+str(gindex)
            if node.ingroup:
                return BQ_group_dict[target] * len(global_arraylist[0])
            else:
                return len(global_arraylist[0])
        else:
            target = "BQ_grouplength_"+str(category)+"_lengthrate_of_"+str(node.arrayid)

        if target not in BQ_group_dict:
            raise ValueError("Array not found")
        return len(global_arraylist[0])
    
    if isinstance(node, DataItemToken):
        pass
    

    # Convert to string and check if it's a BQ_x node (usually "BQ_1", "BQ_2", etc.)
    node_str = str(node)
    if node_str.startswith("BQ_"):
        target = node_str
        return normal_BQ_dict[target] 
    elif node_str.startswith("GBQ_"):
        if category is None:
            raise ValueError("Category is None")
        number = node_str.split("_")[1]
        target = "BQ_group_"+str(category)+"_GBQ_"+ str(number) + "_of_"+ str(gindex) 
        return BQ_group_dict[target]

    # Handle operator nodes
    # Addition
    if isinstance(node, Addition):
        return group_evaluator(node.left, BQ_group_dict, category, gindex=gindex, normal_BQ_dict = normal_BQ_dict) + group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
    # Subtraction
    elif isinstance(node, Subtraction):
        return group_evaluator(node.left, BQ_group_dict, category, gindex=gindex, normal_BQ_dict = normal_BQ_dict) - group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
    # Multiplication
    elif isinstance(node, Multiplication):
        return group_evaluator(node.left, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict) * group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
    # Division
    elif isinstance(node, Division):
        return group_evaluator(node.left, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict) / group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
    # PowerN
    elif isinstance(node, PowerN):
        return group_evaluator(node.base, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict) ** group_evaluator(node.exponent, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)
    
    # If the node has an 'expr' attribute, evaluate that (e.g., Variable node)
    if hasattr(node, "expr"):
        return group_evaluator(node.expr, BQ_group_dict, category, gindex=gindex, normal_BQ_dict= normal_BQ_dict)

    # If the node provides a value() method, use it to evaluate
    if hasattr(node, "value") and callable(node.value):
        return node.value()
    

    # If the node type is not supported, raise an error
    raise TypeError(f"Unsupported node type: {node}")