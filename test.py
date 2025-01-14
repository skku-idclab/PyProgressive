import PyProgress

@PyProgress.transform_decorator
def my_function(x):
    accum = 0
    something = 0
    a = 0
    for idx in range(len(x)):
        accum += x[idx]
        something += 3 
        a += (x[idx]-something)
        print(a)

    return a

if __name__ == "__main__":
    test_list = [10, 20, 30, 21, 5, 42, 11, 14, 34, 13]
    print(my_function(test_list))
    #print(sum(test_list))
