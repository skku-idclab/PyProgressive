import progressive as pp
from progressive.midlevel import each, accum, group_by

if __name__ == "__main__":  
    array0 = pp.Array([('A', 2), ('B', 1), ('A', 4), ('B', 3), ('A', 6), ('B', 5), ('A', 8), ('B', 7), ('A', 10)])
    var = group_by(each(array0, 0), accum(each(array0, 1))/10)

    compiled = pp.progressify(var)
    compiled.run(var, callback = lambda x: print(x))


