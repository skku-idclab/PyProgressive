import PyProgress

@PyProgress.transform_decorator
def my_function(x):
    accum = 0
    for idx in range(len(x)):
        accum += x[idx]
        print(accum)
    average = accum / len(x)  # -> 삭제됨
    return average

if __name__ == "__main__":
    print(my_function([10, 20, 30, 21, 5, 42, 11, 14, 34, 13]))
