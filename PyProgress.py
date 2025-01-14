import ast
import inspect
import copy
import sympy


##############################################################################
# 0) Sympy → 파이썬 AST 변환 도우미
##############################################################################
def sympy_expr_to_ast(symexpr):
    """
    Sympy 표현식(symexpr)을 파이썬 ast 노드로 변환.
    - 숫자, 심볼, Add, Mul, Pow 등 기본 케이스만 처리.
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
        # 기타(예: Div 등)는 간단히 문자열로 fallback
        return ast.Constant(value=str(symexpr))


##############################################################################
# 1) 식 파싱/전개 + 항 계수 추출
##############################################################################
def parse_polynomial(expr_node, idx_var_name='idx'):
    """
    expr_node를 문자열로 -> sympy 전개.
    x[idx]는 X 심볼로 치환.
    
    반환:
      poly_dict    = {k>0: coeff(sympy.Expr)}  (x[idx]^k 항)
      external_sum = x[idx]와 무관한 항들의 합(심볼릭)
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

    poly_dict = {}          # {k>0: coeff_expr}
    external_sum = sympy.Integer(0)  # x[idx] 미포함 항들의 합

    for t in terms:
        c_, k_ = _extract_coeff_power(t, X)
        if k_ == 0:
            external_sum += c_
        else:
            if k_ not in poly_dict:
                poly_dict[k_] = sympy.Integer(0)
            poly_dict[k_] += c_

    return poly_dict, external_sum


def _extract_coeff_power(sym_term, X):
    """
    단일 항(sym_term)에서 X^k 부분을 떼어내고, 나머지를 계수(심볼릭)로 반환.
    예) 3*average*X^2 -> (3*average, 2)
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
        # X 미포함
        return (sym_term, 0)


##############################################################################
# 2) 확장된 LoopTransformer
##############################################################################
class ExtendedLoopTransformer(ast.NodeTransformer):
    """
    (A) 함수 본문에서 "옮길 수 있는 Assign"을 찾아, 
        '해당 Assign'보다 위쪽에서 '가장 최근(last)으로 발견된 for' 의 body 끝에 삽입.
    (B) for idx in range(len(x)): 에서 'accum += ...'를 점진적 평균 로직으로 변환.
    """

    def __init__(self):
        super().__init__()
        self.required_k = set()

    def visit_FunctionDef(self, node):
        """
        1) node.body를 순회하면서, 옮길 Assign이면 '가장 가까운 for' body에 붙이고
           그렇지 않으면 new_body에 남긴다.
        2) 이후 generic_visit으로 for 내부(visit_For) 점진적 변환 수행
        3) 마지막에 required_k 기반 progAvg_k 초기화
        """
        self.required_k.clear()

        new_body = []
        last_for = None  # '가장 가까운 (위쪽) for' 노드

        for stmt in node.body:
            if isinstance(stmt, ast.For):
                # 새로운 for 발견 -> 이게 이제 "가장 최근의 for"
                last_for = stmt
                new_body.append(stmt)
            elif self._should_move_assign(stmt):
                # 옮길 Assign
                if last_for is not None:
                    # last_for.body 끝에 삽입
                    if not isinstance(last_for.body, list):
                        last_for.body = []
                    last_for.body.append(stmt)
                else:
                    # for가 전혀 없는 상황이면 그냥 둔다
                    new_body.append(stmt)
            else:
                # 그대로 둠
                new_body.append(stmt)

        node.body = new_body

        # 이제 기존 로직(visit_For, etc.) 실행
        self.generic_visit(node)

        # required_k만큼 progAvg_k 초기화
        init_stmts = []
        for k in sorted(self.required_k):
            init_stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=f'progAvg_{k}', ctx=ast.Store())],
                    value=ast.Constant(value=0.0)
                )
            )
        # 함수 맨 앞에 삽입
        node.body = init_stmts + node.body

        return node

    def _should_move_assign(self, stmt):
        """
        옮길 조건:
         - stmt가 ast.Assign
         - AugAssign(+=, -=, *=, /=) 아님
         - 좌변이 하나의 Name
         - RHS에 해당 좌변 Name이 등장하지 않음 (자기 자신 참조 X)
        """
        if not isinstance(stmt, ast.Assign):
            return False
        if len(stmt.targets) != 1:
            return False
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            return False

        # AugAssign( a += 3 등 ) 이 아닌지 확인
        # (사실 여긴 "stmt is Assign"이므로 애초에 AugAssign일 일은 없음, 
        #  하지만 혹시 모를 안전체크)
        if isinstance(stmt, ast.AugAssign):
            return False

        assigned_name = target.id
        rhs_names = self._collect_names(stmt.value)
        if assigned_name in rhs_names:
            # s = s+3 처럼 자기 자신 참조
            return False

        return True

    def _collect_names(self, node):
        """
        node 안에 등장하는 모든 ast.Name의 id
        """
        results = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                results.add(child.id)
        return results

    def visit_For(self, node):
        """
        기존 점진적 평균 변환 로직
        """
        self.generic_visit(node)

        # for idx in range(len(x)) 인지 확인
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
            # a += ... 패턴
            if (
                isinstance(stmt, ast.AugAssign)
                and isinstance(stmt.op, ast.Add)
                and isinstance(stmt.target, ast.Name)
            ):
                accum_var = stmt.target.id

                # sympy로 전개
                poly_dict, external_sum = parse_polynomial(stmt.value, idx_var_name=idx_name)
                self.required_k.update(poly_dict.keys())

                # (A) progAvg_k 업데이트(계수 제외)
                for k in sorted(poly_dict.keys()):
                    prog_var = f'progAvg_{k}'

                    left_part = ast.BinOp(
                        left=ast.Name(id=idx_name, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Name(id=prog_var, ctx=ast.Load())
                    )
                    # x[idx]^k
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
                            targets=[ast.Name(id=prog_var, ctx=ast.Store())],
                            value=update_expr
                        )
                    )

                # (B) accum_var = sum_{k}[coeff_k * len(x)*progAvg_k] + len(x)*external_sum
                len_x_call = ast.Call(
                    func=ast.Name(id='len', ctx=ast.Load()),
                    args=[ast.Name(id='x', ctx=ast.Load())],
                    keywords=[]
                )

                sum_expr = None
                for k in sorted(poly_dict.keys()):
                    coeff_ast = sympy_expr_to_ast(poly_dict[k])
                    term_ast = ast.BinOp(
                        left=coeff_ast,
                        op=ast.Mult(),
                        right=ast.BinOp(
                            left=len_x_call,
                            op=ast.Mult(),
                            right=ast.Name(id=f'progAvg_{k}', ctx=ast.Load())
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
def transform_decorator(func):
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
