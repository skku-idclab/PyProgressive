import pyprogressive as pp
from pyprogressive import each, accum
from sklearn.datasets import fetch_california_housing

if __name__ == "__main__":
    pp.reset()
    data = fetch_california_housing(as_frame=True)
    X, y = data.data, data.target

    arrayX1 = pp.array(X["MedInc"].tolist())
    arrayX2 = pp.array(X["HouseAge"].tolist())
    arrayX3 = pp.array(X["AveRooms"].tolist())
    arrayX4 = pp.array(X["AveBedrms"].tolist())
    arrayY  = pp.array(y.tolist())

    mean1 = accum(each(arrayX1)) / len(arrayX1)
    mean2 = accum(each(arrayX2)) / len(arrayX2)
    mean3 = accum(each(arrayX3)) / len(arrayX3)
    mean4 = accum(each(arrayX4)) / len(arrayX4)
    meanY = accum(each(arrayY))  / len(arrayY)

    covX1Y = accum((each(arrayX1) - mean1) * (each(arrayY) - meanY)) / len(arrayX1)
    var1   = accum((each(arrayX1) - mean1) ** 2) / len(arrayX1)
    varY   = accum((each(arrayY)  - meanY) ** 2) / len(arrayY)

    compiled = pp.compile(covX1Y, var1, varY)
    for state in compiled.run(interval=1):
        print(f"{state.progress:.0%} | {state.elapsed:.2f}s | "
              f"cov={state.value(covX1Y):.4f}  "
              f"var1={state.value(var1):.4f}  "
              f"varY={state.value(varY):.4f}")
