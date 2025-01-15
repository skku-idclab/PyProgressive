import ast
import inspect
import copy
import sympy


##############################################################################
# 0) Sympy → Python AST conversion helpers
##############################################################################
def sympy_expr_to_ast(symexpr):
    """
    Convert a Sympy expression (symexpr) into a Python AST node.
    We handle simple cases: numbers, symbols, Add, Mul, Pow, etc.
    """
    if symexpr.is_Number:
        return ast.Constant(value=float(symexpr)) if symexpr.is_Float else ast.Constant(value=int(symexpr))
    elif symexpr.is_Symbol:
        return ast.Name(id=str(symexpr), ctx=ast.Load())
    elif symexpr.is_Add:
        terms = symexpr.as_ordered_terms()
        if not terms:
            return ast.Constant(value=0)
        node = sympy_expr_to_ast(terms[0])
        for t in terms[1:]:
            node = ast.BinOp(left=node, op=ast.Add(), right=sympy_expr_to_ast(t))
        return node
    elif symexpr.is_Mul:
        factors = symexpr.as_ordered_factors()
        if not factors:
            return ast.Constant(value=1)
        node = sympy_expr_to_ast(factors[0])
        for f in factors[1:]:
            node = ast.BinOp(left=node, op=ast.Mult(), right=sympy_expr_to_ast(f))
        return node
    elif symexpr.is_Pow:
        base, exp = symexpr.args
        return ast.Call(
            func=ast.Name(id='pow', ctx=ast.Load()),
            args=[sympy_expr_to_ast(base), sympy_expr_to_ast(exp)],
            keywords=[]
        )
    else:
        # For other cases (like Div, etc.), we fallback to a string representation
        return ast.Constant(value=str(symexpr))


##############################################################################
# 1) Parsing and expansion of expressions + extracting polynomial terms
##############################################################################
def parse_polynomial(expr_node, idx_var_name='idx'):
    """
    1) Convert expr_node (AST) to a string.
    2) Replace x[idx] with the symbol X.
    3) Expand with Sympy.
    4) Separate into polynomial terms in terms of X^k (k>0) and external sums (k=0).
    
    Returns:
      poly_dict: {k>0: coeff (Sympy Expr)}  (terms that include x[idx]^k)
      external_sum: Sympy expression for any part of the expression that does not contain x[idx].
    """
    try:
        from ast import unparse
        expr_str = unparse(expr_node)
    except ImportError:
        import astor
        expr_str = astor.to_source(expr_node).strip()

    expr_str = expr_str.replace(f"x[{idx_var_name}]", "(X)")

    X = sympy.Symbol('X', real=True)
    sym_expr = sympy.sympify(expr_str, {"X": X})
    sym_expr = sympy.expand(sym_expr)

    if sym_expr.is_Add:
        terms = sym_expr.as_ordered_terms()
    else:
        terms = [sym_expr]

    poly_dict = {}
    external_sum = sympy.Integer(0)

    for t in terms:
        c_, k_ = _extract_coeff_power(t, X)
        if k_ == 0:
            # Terms that do not include X
            external_sum += c_
        else:
            # Terms that include X^k
            if k_ not in poly_dict:
                poly_dict[k_] = sympy.Integer(0)
            poly_dict[k_] += c_

    return poly_dict, external_sum


def _extract_coeff_power(sym_term, X):
    """
    Analyze a single term (sym_term), separate out the X^k part,
    and return (coefficient, exponent).
    Examples:
      3*average*X^2 -> (3*average, 2)
      average^2     -> (average^2, 0)
      -2*average*X  -> (-2*average, 1)
    """
    if sym_term.is_Mul:
        factors = sym_term.as_ordered_factors()
        x_power = 0
        coeff = sympy.Integer(1)
        for f in factors:
            if f == X:
                x_power += 1
            elif f.is_Pow and f.args[0] == X:
                x_power += int(f.args[1])
            else:
                coeff *= f
        return (coeff, x_power)

    elif sym_term.is_Pow:
        base, exp = sym_term.args
        if base == X:
            return (sympy.Integer(1), int(exp))
        else:
            return (sym_term, 0)

    elif sym_term == X:
        return (sympy.Integer(1), 1)
    else:
        # Does not include X
        return (sym_term, 0)


##############################################################################
# 2) ExtendedLoopTransformer
##############################################################################
class ExtendedLoopTransformer(ast.NodeTransformer):
    """
    (A) Move certain Assign statements (that can be moved) to the closest preceding
        'for' loop (its body end).
    (B) For 'for idx in range(len(x)):', handle 'accum += ...' by converting it to
        progressive average calculations and final accumulation with coefficients.
    """

    def __init__(self):
        super().__init__()
        self.required_k = set()

    def visit_FunctionDef(self, node):
        """
        1) In the function body, if we find Assign statements that should be moved,
           we move them to the end of the body of the last encountered for-loop above.
        2) Then we apply generic_visit to handle for-loops (visit_For) for progressive calc.
        3) After that, insert the BQ_{k} = 0.0 initializations at the start
           for all required_k.
        """
        self.required_k.clear()

        new_body = []
        last_for = None  # The most recently encountered for-loop

        for stmt in node.body:
            if isinstance(stmt, ast.For):
                last_for = stmt
                new_body.append(stmt)
            elif self._should_move_assign(stmt):
                # Move this statement to the end of last_for.body if possible
                if last_for is not None:
                    if not isinstance(last_for.body, list):
                        last_for.body = []
                    last_for.body.append(stmt)
                else:
                    # If there's no for-loop found yet, keep it as is
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        node.body = new_body

        # Proceed with the rest of transformations
        self.generic_visit(node)

        # Insert BQ_{k} initializations at the top of the function
        init_stmts = []
        for k in sorted(self.required_k):
            init_stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=f'BQ_{k}', ctx=ast.Store())],
                    value=ast.Constant(value=0.0)
                )
            )
        node.body = init_stmts + node.body

        return node

    def _should_move_assign(self, stmt):
        """
        Decide if we should move this Assign to the nearest preceding for-loop.
        Conditions:
         - stmt is ast.Assign
         - Not an AugAssign (like +=)
         - Single target, which is a Name
         - RHS does not refer to the same Name (no self-reference)
        """
        if not isinstance(stmt, ast.Assign):
            return False
        if len(stmt.targets) != 1:
            return False
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            return False

        # If it was AugAssign, skip (though by definition it's not an Assign, but let's be safe)
        if isinstance(stmt, ast.AugAssign):
            return False

        assigned_name = target.id
        rhs_names = self._collect_names(stmt.value)
        if assigned_name in rhs_names:
            # self-reference e.g., s = s + 3
            return False

        return True

    def _collect_names(self, node):
        """
        Collect all ast.Name ids inside the given node.
        """
        results = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                results.add(child.id)
        return results

    def visit_For(self, node):
        """
        Transform 'accum += something' inside 'for idx in range(len(x)):' 
        into progressive average updates + final accumulation.
        """
        self.generic_visit(node)

        # Check if it's for idx in range(len(x)):
        if not (
            isinstance(node.target, ast.Name)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == 'range'
        ):
            return node

        args = node.iter.args
        if len(args) == 1:
            len_call = args[0]
        elif len(args) == 2:
            len_call = args[1]
        else:
            return node

        if not (
            isinstance(len_call, ast.Call)
            and isinstance(len_call.func, ast.Name)
            and len_call.func.id == 'len'
            and len_call.args
            and isinstance(len_call.args[0], ast.Name)
            and len_call.args[0].id == 'x'
        ):
            return node

        idx_name = node.target.id
        new_body = []

        for stmt in node.body:
            # Look for accum += ...
            if (
                isinstance(stmt, ast.AugAssign)
                and isinstance(stmt.op, ast.Add)
                and isinstance(stmt.target, ast.Name)
            ):
                accum_var = stmt.target.id

                # Parse with Sympy
                poly_dict, external_sum = parse_polynomial(stmt.value, idx_var_name=idx_name)
                self.required_k.update(poly_dict.keys())

                # (A) BQ_{k} = (idx * BQ_{k} + x[idx]^k) / (idx + 1)
                # (Coefficient is not applied here)
                for k in sorted(poly_dict.keys()):
                    bq_var = f'BQ_{k}'

                    left_part = ast.BinOp(
                        left=ast.Name(id=idx_name, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Name(id=bq_var, ctx=ast.Load())
                    )
                    x_sub = ast.Subscript(
                        value=ast.Name(id='x', ctx=ast.Load()),
                        slice=ast.Name(id=idx_name, ctx=ast.Load()),
                        ctx=ast.Load()
                    )
                    pow_call = ast.Call(
                        func=ast.Name(id='pow', ctx=ast.Load()),
                        args=[x_sub, ast.Constant(value=k)],
                        keywords=[]
                    )
                    plus_part = ast.BinOp(left=left_part, op=ast.Add(), right=pow_call)
                    denominator = ast.BinOp(
                        left=ast.Name(id=idx_name, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Constant(value=1)
                    )
                    update_expr = ast.BinOp(left=plus_part, op=ast.Div(), right=denominator)

                    new_body.append(
                        ast.Assign(
                            targets=[ast.Name(id=bq_var, ctx=ast.Store())],
                            value=update_expr
                        )
                    )

                # (B) accum_var = sum_{k}[coeff_k * len(x)*BQ_{k}] + len(x)*external_sum
                len_x_call = ast.Call(
                    func=ast.Name(id='len', ctx=ast.Load()),
                    args=[ast.Name(id='x', ctx=ast.Load())],
                    keywords=[]
                )
                sum_expr = None

                for k in sorted(poly_dict.keys()):
                    coeff_ast = sympy_expr_to_ast(poly_dict[k])
                    # term = coeff_k * len(x)*BQ_{k}
                    term_ast = ast.BinOp(
                        left=coeff_ast,
                        op=ast.Mult(),
                        right=ast.BinOp(
                            left=len_x_call,
                            op=ast.Mult(),
                            right=ast.Name(id=f'BQ_{k}', ctx=ast.Load())
                        )
                    )
                    if sum_expr is None:
                        sum_expr = term_ast
                    else:
                        sum_expr = ast.BinOp(left=sum_expr, op=ast.Add(), right=term_ast)

                if external_sum != 0:
                    ext_ast = sympy_expr_to_ast(external_sum)
                    ext_term = ast.BinOp(left=len_x_call, op=ast.Mult(), right=ext_ast)
                    if sum_expr is None:
                        sum_expr = ext_term
                    else:
                        sum_expr = ast.BinOp(left=sum_expr, op=ast.Add(), right=ext_term)

                if sum_expr is not None:
                    new_body.append(
                        ast.Assign(
                            targets=[ast.Name(id=accum_var, ctx=ast.Store())],
                            value=sum_expr
                        )
                    )
                else:
                    new_body.append(stmt)

            else:
                new_body.append(stmt)

        node.body = new_body
        return node


##############################################################################
# 3) transform_decorator
##############################################################################
def fy(func):
    if getattr(func, '__transformed__', False):
        return func

    source = inspect.getsource(func)
    lines = source.split('\n')
    filtered_lines = [line for line in lines if not line.strip().startswith('@')]
    new_source = '\n'.join(filtered_lines)

    tree = ast.parse(new_source)
    transformer = ExtendedLoopTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    print(ast.unparse(new_tree))

    code = compile(new_tree, filename="<ast-transform>", mode="exec")
    new_globals = copy.copy(func.__globals__)
    exec(code, new_globals)

    transformed_func = new_globals[func.__name__]
    transformed_func.__name__ = func.__name__
    transformed_func.__doc__ = func.__doc__
    transformed_func.__module__ = func.__module__
    transformed_func.__transformed__ = True

    return transformed_func
