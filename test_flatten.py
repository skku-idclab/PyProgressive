
import progressive as pp  

def test_flatten_operations():
    # Create a session
    session = pp.Session()

    # Create an Array (though in this simple test, we might not heavily use it)
    arr = pp.Array([10, 20, 30])

    # Start a Loop context
    with session.loop(arr) as loop:
        # Create a few variables
        # v1 starts at 0
        v1 = loop.add_variable(0)

        # Perform nested additions/subtractions on v1
        # For instance: v1 = 0 + (5 - (2 + 3))
        for i in loop:
            v1+=arr[i]

        v1 += 5
        v1 -= (2 + 3)

        # Another variable, v2 = 10
        v2 = loop.add_variable(10)

        # Let’s do something like: v2 = 10 + (v1 - 7)
        v2 += (v1 - 7)

        # We could also nest further if we want to test deeper flatten:
        # v2 = v2 + ((v1 + 2) - (5 + 4))
        #   => v2 = (10 + (v1 - 7)) + ((v1 + 2) - (5 + 4))
        v2 += ((v1 + 2) - (5 + 4))

        # Because of operator overloading, each line builds up the expression tree.
        # When we exit the 'with' block:
        #   - The loop's __exit__ will do a topological sort and flatten Add/Sub.
        #   - We'll see the flattened result printed out.


if __name__ == "__main__":
    test_flatten_operations()
