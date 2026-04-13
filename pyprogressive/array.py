

global_arraylist = []

def reset():
    """Clear all tracked arrays and reset the id counter.
    Call this at the start of each independent computation to avoid
    leftover arrays from previous cells causing length-mismatch errors.
    Also resets the live vis chart state if pyprogressive.vis is imported.
    """
    import sys
    global_arraylist.clear()
    array._id = 0
    vis = sys.modules.get('pyprogressive.vis')
    if vis is not None:
        vis._live_reset()

class array:
    _id = 0
    def __init__(self, data):
        # Normalize pandas Series/DataFrame columns: their index may be non-contiguous
        # after dropna() or boolean filtering, causing KeyError on integer access.
        if hasattr(data, 'iloc'):
            data = data.tolist()
        elif not isinstance(data, list):
            # Accept any iterable (zip, generator, tuple, …) by materialising it.
            data = list(data)
            # Unwrap 1-element tuples produced by zip(single_iterable).
            # zip(series) yields (val,) tuples; the downstream BQ code expects
            # plain scalars for non-grouped data.
            if data and isinstance(data[0], tuple) and len(data[0]) == 1:
                data = [x[0] for x in data]
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
 