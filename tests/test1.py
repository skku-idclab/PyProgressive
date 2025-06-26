import pyprogressive as pp
from pyprogressive.midlevel import each, accum, group, G

# A: 2 -3 10 8 10 0
# B: 1 4 7 -5
# C: 2 3
array0 = pp.array([('A', 2), ('C', 2), ('B', 1), ('B', 4), ('C', 3), ('A', -3),
                   ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('B', -5), ('A', 0)])


mean = accum(each(array0, 1)) / accum(1)
group_mean = group(each(array0, 0), accum(each(G, 1)) / accum(1))

compiled = pp.compile(mean, group_mean)
compiled.run(interval = 0, callback = lambda mean, group_mean: print(mean, group_mean))

# Traceback (most recent call last):
#   File "c:\Users\zxcva\Desktop\@@\SKKU\산학\PyProgressive_Code\tests\test.py", line 15, in <module>     
#     compiled.run(interval=1, callback=lambda mean, group_mean: print(mean, group_mean))
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\midlevel.py", line 249, in run
#     result = evaluate(var, BQ_dict, length = len(global_arraylist[0]))
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 50, in evaluate
#     return evaluate(node.left, bq_values, length) / evaluate(node.right, bq_values, length)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 47, in evaluate
#     return evaluate(node.left, bq_values, length) * evaluate(node.right, bq_values, length)

# TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'