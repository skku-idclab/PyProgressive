import pyprogressive as pp
from pyprogressive.midlevel import each, accum, group, G


x = pp.array([1, 3, 5, 7, 9, 11, 13])
y = pp.array([1, 1, 2, 3, 5, 8, 13])

mx = accum(each(x)) / accum(1)
my = accum(each(y)) / accum(1)

var_x = accum((each(x) - mx) ** 2) / accum(1)
cov = accum((each(x) - mx) * (each(y) - my)) / accum(1)

beta = cov / (var_x+1e-12)

compiled = pp.compile(mx, my, cov, beta)
compiled.run(interval = 0, callback = print)


# Traceback (most recent call last):
#   File "c:\Users\zxcva\Desktop\@@\SKKU\산학\PyProgressive\tests\test3.py", line 14, in <module>
#     compiled.run(interval = 1, callback = print)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\midlevel.py", line 249, in run
#     result = evaluate(var, BQ_dict, lengtssh = len(global_arraylist[0]))
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 50, in evaluate
#     return evaluate(node.left, bq_values, length) / evaluate(node.right, bq_values, length)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 47, in evaluate
#     return evaluate(node.left, bq_values, length) * evaluate(node.right, bq_values, length)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 57, in evaluate
#     return evaluate(node.expr, bq_values, length)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 47, in evaluate
#     return evaluate(node.left, bq_values, length) * evaluate(node.right, bq_values, length)
#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 53, in evaluate
#     return evaluate(node.base, bq_values, length) ** evaluate(node.exponent, bq_values, length)
# TypeError: unsupported operand type(s) for ** or pow(): 'NoneType' and 'int'