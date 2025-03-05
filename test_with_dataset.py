import progressive as pp
from sklearn.datasets import fetch_california_housing
import pandas as pd


data = fetch_california_housing(as_frame=True)

X = data.data
y = data.target

X = X["MedInc"]

Xlist = X.tolist()
ylist = y.tolist()

ps = pp.Session()
arrayX = pp.Array(Xlist)
arrayY = pp.Array(ylist)

with ps.loop([arrayX, arrayY], interval=0.1) as loop:
    xmean = loop.add_variable(0)
    xstd = loop.add_variable(0)
    ymean = loop.add_variable(0)
    ystd = loop.add_variable(0)
    
    
    

    @loop.on("tick")
    def tick_handler():
        print(round(xmean.value(), 4), round(ymean.value(), 4), round(cov.value(), 4), round(abs(cor.value())**0.5, 4))

    @loop.on("end")
    def end_handler():
        print("Computation end")
        print(xmean.value(), ymean.value(), cov.value(), abs(cor.value())**0.5)
    
    for i in loop:
        xmean += arrayX[i]
    xmean /= len(arrayX)

    for i in loop:
        xstd += (arrayX[i] - xmean) ** 2
    xstd /= len(arrayX)-1

    for i in loop:
        ymean += arrayY[i]
    ymean /= len(arrayX)

    for i in loop:
        ystd += (arrayY[i] - ymean) ** 2
    ystd /= len(arrayX)-1

    cov = loop.add_variable(0)

    for i in loop:
        cov += (arrayX[i] - xmean) * (arrayY[i] - ymean)
    cov /= len(arrayX)-1

    cor = loop.add_variable(0)

    for i in loop:
        cor += 0
    
    cor += cov**2
    cor /= xstd +1e-9
    cor /= ystd +1e-9
