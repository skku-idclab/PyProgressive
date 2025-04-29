import pyprogressive as pp
from sklearn.datasets import fetch_california_housing
import pandas as pd
from pyprogressive.midlevel import each, accum

data = fetch_california_housing(as_frame=True)

X = data.data
y = data.target

X1 = X["MedInc"]
X2 = X["HouseAge"]
X3 = X["AveRooms"]
X4 = X["AveBedrms"]

X1list = X1.tolist()
X2list = X2.tolist()
X3list = X3.tolist()
X4list = X4.tolist()

ylist = y.tolist()

arrayX1 = pp.Array(X1list)
arrayX2 = pp.Array(X2list)
arrayX3 = pp.Array(X3list)
arrayX4 = pp.Array(X4list)
arrayY = pp.Array(ylist)

mean1 = accum(each(arrayX1)) / len(arrayX1)
# mean2 = accum(each(arrayX2)) / len(arrayX2)
# mean3 = accum(each(arrayX3)) / len(arrayX3)
# mean4 = accum(each(arrayX4)) / len(arrayX4)
meanY = accum(each(arrayY)) / len(arrayY)

var1 = accum((each(arrayX1)-mean1)**2)/len(arrayX1)
# var2 = accum((each(arrayX2)-mean2)**2)/len(arrayX2)
# var3 = accum((each(arrayX3)-mean3)**2)/len(arrayX3)
# var4 = accum((each(arrayX4)-mean4)**2)/len(arrayX4)
varY = accum((each(arrayY)-meanY)**2)/len(arrayY)

covX1Y = accum((each(arrayX1)-mean1)*(each(arrayY)-meanY)) / len(arrayX1)
# covX2Y = accum((each(arrayX2)-mean2)*(each(arrayY)-meanY)) / len(arrayX2)
# covX3Y = accum((each(arrayX3)-mean3)*(each(arrayY)-meanY)) / len(arrayX3)
# covX4Y = accum((each(arrayX4)-mean4)*(each(arrayY)-meanY)) / len(arrayX4)

def mycallback(cov1,var1,varY, elapsed):
    print(cov1, var1, varY, elapsed)



compiled = pp.compile(covX1Y,var1, varY)
compiled.run(callback = mycallback)

