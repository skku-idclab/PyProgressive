import pyprogressive as pp
from pyprogressive.midlevel import each, accum, group, G

if __name__ == "__main__":  
    array = pp.array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
    array0 = pp.array([('A', 2), ('B', 1), ('B', 4), ('C', 3), ('A', -3), ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('A', 0)])
    array1 = pp.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    wholesum = accum(each(array0, 1))
    var = group(each(array0, 0), accum(each(G, 1)))
    var2 = group(each(array0, 0), accum(each(G, 1))/accum(1))

    compiled = pp.compile(wholesum, var ,var2)
    compiled.run(interval = 0, callback = lambda wholesum, var, var2: print(wholesum, var, var2))



