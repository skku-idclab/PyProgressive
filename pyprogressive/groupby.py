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
        item = array.data[idx]
        group_key = item if group_index == -1 else item[group_index]
        BQ_str_grouplength_rate = "BQ_grouplength_"+str(group_key)+"_lengthrate_of_"+str(array_index)
        BQ_str_eval = "BQ_group_"+str(group_key)+"_"
        BQ_str_dict = {}

        _, BQ_str_dict = group_convert_with_bq(expr.expr, BQ_str_dict)

        # Store key-column metadata so group_by_bq_update can use the right column
        BQ_dict[f"META_groupindex_of_{array_index}"] = group_index

        for key in BQ_str_dict.keys():
            if key.startswith("GBQ"):
                num = key.split("_")[1]
                col_str = key.split("_")[-1]
                try:
                    val_col = int(col_str)
                except ValueError:
                    val_col = 1  # legacy fallback
                tem = BQ_str_eval + "GBQ_" + str(num) + "_of_" + str(array_index)
                if tem not in BQ_dict:
                    BQ_dict[tem] = 0
                # Store value-column metadata for this GBQ key
                BQ_dict[f"META_col_{tem}"] = val_col
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
            group_index = BQ_dict.get(f"META_groupindex_of_{using_array_idx}", 0)
            group_key = str(item) if not isinstance(item, tuple) else str(item[group_index])
            if key_str[2] == group_key:
                BQ_dict[key] = (BQ_dict[key] * idx + 1) / (idx + 1)
            else:
                BQ_dict[key] = BQ_dict[key] * idx / (idx + 1)

    for key in BQ_dict.keys():
        if not key.startswith("BQ_group"):
            continue
        key_str = key.split("_")
        using_array_idx = key_str[-1]
        using_array = global_arraylist[int(using_array_idx)]
        item = using_array.data[idx]
        group_index = BQ_dict.get(f"META_groupindex_of_{using_array_idx}", 0)
        group_key = str(item) if not isinstance(item, tuple) else str(item[group_index])
        if key_str[1] == "group" and key_str[2] == group_key:
            degree, compute_arr = key_str[4], key_str[6]
            target_arr = None
            for arr in global_arraylist:
                if arr.id == int(compute_arr):
                    target_arr = arr
            if target_arr is None:
                raise ValueError("Array not found")

            # Look up actual value column from metadata (set by detect_group_bq)
            val_col = BQ_dict.get(f"META_col_{key}", None)
            if val_col is not None:
                # GBQ key: value comes from item[val_col] of the grouped array
                val = item if not isinstance(item, tuple) else item[val_col]
            else:
                # Non-GBQ key: value comes from target array (legacy path)
                target_item = target_arr.data[idx]
                val = target_item if not isinstance(target_item, tuple) else target_item[1]

            category = key_str[2]
            category_lengthrate = BQ_dict["BQ_grouplength_" + category + "_lengthrate_of_" + str(compute_arr)]
            category_length = category_lengthrate * (idx + 1)
            BQ_dict[key] = (BQ_dict[key] * (category_length - 1) + val ** int(degree)) / category_length

    return BQ_dict


def group_evaluator(var, BQ_group_dict, category=None, index=None, gindex=None, normal_BQ_dict=None):
    node = var
    if isinstance(node, GroupBy):
        categoryies = set()
        category_values = {}
        for key in BQ_group_dict.keys():
            if key.startswith("BQ_group"):
                categoryies.add(key.split("_")[2])

        for target_category in categoryies:
            category_values[target_category] = group_evaluator(
                node.expr, BQ_group_dict,
                category=target_category, gindex=gindex,
                normal_BQ_dict=normal_BQ_dict,
            )

        node.val = category_values
        return category_values

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

    node_str = str(node)
    if node_str.startswith("BQ_"):
        return normal_BQ_dict[node_str]
    elif node_str.startswith("GBQ_"):
        if category is None:
            raise ValueError("Category is None")
        number = node_str.split("_")[1]
        target = "BQ_group_"+str(category)+"_GBQ_"+str(number)+"_of_"+str(gindex)
        return BQ_group_dict[target]

    if isinstance(node, Addition):
        return (group_evaluator(node.left,  BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict) +
                group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict))
    elif isinstance(node, Subtraction):
        return (group_evaluator(node.left,  BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict) -
                group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict))
    elif isinstance(node, Multiplication):
        return (group_evaluator(node.left,  BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict) *
                group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict))
    elif isinstance(node, Division):
        return (group_evaluator(node.left,  BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict) /
                group_evaluator(node.right, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict))
    elif isinstance(node, PowerN):
        return (group_evaluator(node.base,     BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict) **
                group_evaluator(node.exponent, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict))

    if hasattr(node, "expr"):
        return group_evaluator(node.expr, BQ_group_dict, category, gindex=gindex, normal_BQ_dict=normal_BQ_dict)

    if hasattr(node, "value") and callable(node.value):
        return node.value()

    raise TypeError(f"Unsupported node type: {node}")
