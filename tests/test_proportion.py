import pyprogressive as pp
from pyprogressive import G, accum, each, group

if __name__ == "__main__":
    pp.reset()
    D = pp.array([("A", 1), ("B", 4), ("A", 2), ("C", 3)])
    total       = accum(each(D, 1))
    proportions = group(each(D, 0), accum(each(G, 1)) / total)

    program = pp.compile(proportions)
    for state in program.run(interval=1):
        print(f"{state.progress:.0%} | {state.value(proportions)}")
