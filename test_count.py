import progressive as pp
from progressive import each, accum, group, G

if __name__ == "__main__":  
    array0 = pp.Array(["A", "B", "B", "C", "A", "A", "A", "B", "A", "A"])
    count = group(each(array0), accum(1))

    compiled = pp.compile(count)
    compiled.run(interval = 0, callback = print)