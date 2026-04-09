

global_arraylist = []

def reset():
    """Clear all tracked arrays and reset the id counter.
    Call this at the start of each independent computation to avoid
    leftover arrays from previous cells causing length-mismatch errors.
    """
    global_arraylist.clear()
    array._id = 0

class array:
    _id = 0
    def __init__(self, data):
        # Normalize pandas Series/DataFrame columns: their index may be non-contiguous
        # after dropna() or boolean filtering, causing KeyError on integer access.
        if hasattr(data, 'iloc'):
            data = data.tolist()
        self.data = data
        self.length = len(data)
        self.iter = 0
        self.id = array._id
        global_arraylist.append(self)
        array._id += 1

    
    def __len__(self):        
        return self.length #DataLengthToken(self)
    
    def __str__(self):
        return "Array_" + str(self.id)
 