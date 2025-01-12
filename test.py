import PyProgress

@PyProgress.transform_decorator
def my_function2(x):
    accum = 0
    for idx in range(len(x)):
        accum += x[idx]
    average = accum / len(x)  # -> 삭제됨
    return average
if __name__ == "__main__":
    print(my_function2([10, 20, 30]))
