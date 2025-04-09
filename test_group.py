import progressive as pp
from progressive.midlevel import each, accum, group

if __name__ == "__main__":  
    array = pp.Array([2, 4, 6, 8, 10, 12, 14, 16, 18])
    array0 = pp.Array([('A', 2), ('B', 100), ('A', 4), ('B', 3), ('A', 6000), ('B', 5), ('A', 8), ('B', 7), ('A', 10)])

    var = group(each(array0, 0), accum(each(array0, 1))/10)

    compiled = pp.compile(var)
    compiled.run(interval = 0, callback = lambda x: print(x))

    


