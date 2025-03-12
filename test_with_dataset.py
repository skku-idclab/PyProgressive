import progressive as pp
from sklearn.datasets import fetch_california_housing
import pandas as pd


data = fetch_california_housing(as_frame=True)

X = data.data
y = data.target

X1 = X["MedInc"]
X2 = X["HouseAge"]
X3 = X["AveRooms"]
X4 = X["AveBedRooms"]

X1list = X.tolist()
ylist = y.tolist()

arrayX = pp.Array(X1list)
arrayY = pp.Array(ylist)


