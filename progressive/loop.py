# from .estimator.simple_linear_estimator import SimpleLinearEstimator
# from .tick import Tick

from .token import SpecialToken
from .variable import Variable
from .expression import Node, Addition, Subtraction, Multiplication, Division, PowerN, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision
from .flatten_utils import flatten_add_sub

class Loop:
    def __init__(self, session, array, interval=1):
        self.session = session
        self.array = array
        self.interval = interval

        self.cursor_in_loop = False
        self.variables = []
        self.handlers = []
        self.symbol = SpecialToken.LOOP_INDEX        
    
    def __enter__(self):    
        return self
        
    def add_variable(self, value):
        v = Variable(self, value)
        self.variables.append(v)
        return v

    def __exit__(self, *args):
        self.variables[0].print()
        self.variables[1].print()
        # TODO: topological sort
        # TODO: check for cycles
        # TODO: flatten additions and subtractions        
        # TODO: flatten multiplications
        # TODO: check if each expr can be projected by BQs


        #1) topological sort
        root_nodes = [var.expr for var in self.variables]

        print("Root nodes:")
        for node in root_nodes:
            print(node)

        # Sort the nodes in topological order
        sorted_nodes = self._topological_sort(root_nodes)

        print("Sorted nodes:")
        for node in sorted_nodes:
            print(node)

        #2) flatten additions and subtractions
        for i, var in enumerate(self.variables):
            self.variables[i].expr = flatten_add_sub(var.expr)

        print("\nFlattened nodes:")
        for i, var in enumerate(self.variables):
            print(f"Variable {i}: {var.print()}")

                
        # compile
        
        
        # run with time estimators
        
        #print(args)
        pass
    
    def __iter__(self):        
        if self.cursor_in_loop: 
            raise "Nested loops are not supported!"
        return self

    def __next__(self):
        if not self.cursor_in_loop:
            self.cursor_in_loop = True
            
            return self.symbol         
                   
        self.cursor_in_loop = False        
        raise StopIteration  # Stop iteration after yielding once

    # def __iter__(self):
    #     self.emit("start")

    #     self.iter = None
    #     self.array.init_iter()
    #     self.estimator = SimpleLinearEstimator()

    #     return self
    
    # def __next__(self):
    #     if self.iter:
    #         self.array.update_iter(self.iter)
    #         self.estimator.end()
            
    #         self.emit("tick")

    #         self.iter = None

    #     if self.array.iter_done():
    #         self.emit("end")
    #         raise StopIteration
        
    #     iter_from = self.array.iter
    #     iter_to = self.array.iter + self.estimator.estimate_next(self.tick)
    #     iter_to = min(iter_to, self.array.length)

    #     self.iter = iter_to
    #     self.estimator.start()

    #     return Tick(self.array, iter_from, iter_to)

    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator
    
    def emit(self, event, *args):
        for event_name, handler in self.handlers:
            if event_name == event:
                handler(*args)


    def _get_children(self, node):
        """
        Returns a list of child nodes for the given node (Variable, Addition, etc.).

        Args:
            node (Node): The node for which to find children.

        Returns:
            list[Node]: A list of child nodes.
        """
        if isinstance(node, (Addition, Subtraction, Multiplication, Division, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision)):
            return [node.left, node.right]
        elif isinstance(node, PowerN):
            return [node.base, node.exponent]
        elif isinstance(node, Variable):
            # Variable also inherits from Node, but keeps its main expression in 'self.expr'.
            if hasattr(node, "expr"):
                return [node.expr]
            else:
                return []
        else:
            # For constants, tokens, or other terminal objects, no children.
            return []


    def _topological_sort(self, root_nodes):
        """
        Performs DFS-based topological sorting (with cycle detection) on
        the expression graph formed by the root nodes.

        Args:
            root_nodes (list[Node]): A list of expression roots (e.g., psum.expr, pssum.expr).

        Returns:
            list[Node]: A list of nodes in topologically sorted order.

        Raises:
            RuntimeError: If a cycle is detected in the expression graph.
        """
        visited = set()
        in_stack = set()  # Tracks nodes in the current DFS recursion path
        sorted_list = []
        self.has_cycle = False

        def dfs(node):
            if node in in_stack:
                # Cycle found if the node is already in the current recursion stack
                self.has_cycle = True
                return
            if node in visited:
                # Skip nodes that have already been fully processed
                return

            in_stack.add(node)
            

            # Visit child nodes (if they are Node instances)
            for child in self._get_children(node):
                if isinstance(child, Node):
                    dfs(child)

            in_stack.remove(node)
            visited.add(node)

            sorted_list.append(node)

        # Start DFS from each root node
        for root in root_nodes:
            if root is not None and root not in visited:
                dfs(root)

        # If a cycle was detected, raise an error.
        if self.has_cycle:
            raise RuntimeError("Cycle detected in expression graph!")

        # Reverse the list to get the proper topological order
        #sorted_list.reverse()
        return sorted_list
