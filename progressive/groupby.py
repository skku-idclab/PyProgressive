from .expression import Node, GroupBy, InplaceOperationNode, BinaryOperationNode, BQ
from .bq_converter import convert_with_bq
from .array import Array, global_arraylist
def group_by_bq_evaluator(expr, BQ_dict, idx):
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
            print("key_str: ", key_str)
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
                    print("cateogry: ", cateogry)
                    category_lengthrate = BQ_dict["BQ_grouplength_"+cateogry+"_lengthrate_of_"+str(compute_arr)]
                    category_length = category_lengthrate * (idx+1) 
                    BQ_dict[key] = (BQ_dict[key] * (category_length-1) + item[1] ** (int(degree))) / category_length # TODO: Data Item Indexing
        print("BQ_dict: ", BQ_dict)


        if not isinstance(item, tuple):
            raise ValueError("Array item must be a tuple in group operation")
        
        
        return GroupBy(group_index, array_index, expr), BQ_dict
    else:
        raise ValueError("Invalid expression for group_by_converter")
    