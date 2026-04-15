import pyprogressive as pp
from pyprogressive import each, accum

if __name__ == "__main__":
    pp.reset()
    array0 = pp.array([1, 2, 3, 4, 5, 6])
    mean = accum(each(array0)) / len(array0)

    compiled = pp.compile(mean)
    for state in compiled.run(interval=0):
        pass

    print(f"mean = {state.value(mean):.4f}")   # expected: 3.5
