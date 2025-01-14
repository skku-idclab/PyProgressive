import ast
import inspect
import copy
import sympy

##############################################################################
# 0) 심볼릭 → 파이썬 AST 변환 도우미 함수
##############################################################################
def sympy_expr_to_ast(symexpr):
    """
    Sympy 표현식(symexpr)을 파이썬 ast.Expression 형태로 변환하는 간단한 예시.
    - 여기서는 숫자, 심볼, Mul, Add, Pow 등 기본 케이스만 처리.
    - 더 복잡한 심볼릭(함수호출 등)은 별도 확장 필요.
    """
    if symexpr.is_Number:
        # 정수, 부동소수 등
        # Python 3.8+ 에서는 ast.Constant, 이하에서는 ast.Num
        return ast.Constant(value=float(symexpr)) if symexpr.is_Float else ast.Constant(value=int(symexpr))

    elif symexpr.is_Symbol:
        # Sympy 심볼이 예: Symbol('average'), Symbol('X') 등
        # 여기서 'X'는 실제론 쓰이지 않을 것이고,
        # 'average' 같은 외부 변수를 가리킬 수 있음
        return ast.Name(id=str(symexpr), ctx=ast.Load())

    elif symexpr.is_Add:
        # 덧셈의 경우, 예: a + b + c...
        # as_ordered_terms()로 각 항을 나누고 순차적으로 BinOp로 연결
        terms = symexpr.as_ordered_terms()
        if not terms:
            return ast.Constant(value=0)
        result_ast = sympy_expr_to_ast(terms[0])
        for term in terms[1:]:
            result_ast = ast.BinOp(
                left=result_ast,
                op=ast.Add(),
                right=sympy_expr_to_ast(term)
            )
        return result_ast

    elif symexpr.is_Mul:
        # 곱셈
        factors = symexpr.as_ordered_factors()
        if not factors:
            return ast.Constant(value=1)
        result_ast = sympy_expr_to_ast(factors[0])
        for f in factors[1:]:
            result_ast = ast.BinOp(
                left=result_ast,
                op=ast.Mult(),
                right=sympy_expr_to_ast(f)
            )
        return result_ast

    elif symexpr.is_Pow:
        # 거듭제곱
        base, exp = symexpr.args
        return ast.Call(
            func=ast.Name(id='pow', ctx=ast.Load()),
            args=[sympy_expr_to_ast(base), sympy_expr_to_ast(exp)],
            keywords=[]
        )

    else:
        # 기타 케이스 (예: Div, etc.) 필요시 확장
        # 여기서는 간단히 str(symexpr)를 literal_eval 할 수 없으므로,
        # Sympy -> 문자열 -> ast.parse() 식으로도 갈 수 있음.
        # 우선 예제에서는 Add, Mul, Pow, Number, Symbol만 처리한다고 가정.
        return ast.Constant(value=str(symexpr))


##############################################################################
# 1) 식 파싱/전개 + 항 계수 추출 (Sympy 활용)
##############################################################################
def parse_polynomial(expr_node, idx_var_name='idx'):
    """
    (x[idx])만 심볼릭 상수 'X'로 치환하고, Sympy로 전개한 뒤
    => {차수 k: sympy_expr 계수} 형태로 리턴.
    
    예: (x[idx] - average)**2
      -> X^2 - 2*average*X + average^2
      -> {2: 1, 1: -2*average, 0: average^2}
    """
    # 1) expr_node -> 문자열
    try:
        from ast import unparse
        expr_str = unparse(expr_node)
    except ImportError:
        # Python 3.8 미만인 경우 astor 사용 (데모용)
        import astor
        expr_str = astor.to_source(expr_node).strip()

    # 2) "x[idx]" -> "X" 치환
    expr_str = expr_str.replace(f"x[{idx_var_name}]", "(X)")

    # 3) Sympy 변환 + 전개
    X = sympy.Symbol('X', real=True)
    sym_expr = sympy.sympify(expr_str, {"X": X})
    sym_expr = sympy.expand(sym_expr)

    # 4) 각 항을 분석 -> {차수 k: 계수(심볼릭)}
    #    ex) x[idx]^2 -> k=2, coeff=1
    #        x[idx] -> k=1, coeff=some_expr
    #        (외부변수)*x[idx] -> k=1, coeff=(외부변수)
    #        상수항 -> k=0, coeff=(어떤 표현)
    poly_dict = {}
    if sym_expr.is_Add:
        terms = sym_expr.as_ordered_terms()
    else:
        terms = [sym_expr]

    for t in terms:
        c_, k_ = _extract_coeff_power(t, X)
        # c_는 sympy.Expr(계수), k_는 int(차수)
        if k_ not in poly_dict:
            poly_dict[k_] = sympy.Integer(0)  # 누적용
        poly_dict[k_] += c_

    return poly_dict  # {k: sympy.Expr, ...}


def _extract_coeff_power(sym_term, X):
    """
    sym_term(단일 항)을 분석하여,  X^k 부분과 나머지 계수(심볼릭) 분리.
    예) 3*average*X^2 -> (3*average, 2)
        X -> (1, 1)
        -2*average*X -> (-2*average, 1)
        average^2 -> (average^2, 0)
    """
    # 1) 먼저 X^k 형태로 X 부분을 떼어내고, 나머지는 계수로 본다.
    #    sympy의 as_base_exp, as_coefficient, etc. 활용 가능.
    #    여기서는 직접 분기.

    # (A) X^k 자체인 경우
    if sym_term.is_Pow:
        # 예: X^k
        base, exp = sym_term.args
        if base == X:
            return (sympy.Integer(1), int(exp))  # coeff=1, pow=exp
        else:
            # ex) (something_else)^k
            return (sym_term, 0)  # X와 무관 -> k=0
    elif sym_term == X:
        # ex) X
        return (sympy.Integer(1), 1)
    elif sym_term.is_Symbol and sym_term != X:
        # 예) average
        # -> X와 무관 -> k=0, coeff=sym_term(average)
        return (sym_term, 0)
    elif sym_term.is_Number:
        # 예) 5
        return (sym_term, 0)
    elif sym_term.is_Mul:
        # 예) 3*average*X^2,  (something)*X^k
        # factor 중 X^k 부분 찾기
        # 나머지는 계수
        factors = sym_term.as_ordered_factors()

        x_power = 0
        coeff_expr = sympy.Integer(1)
        for f in factors:
            if f == X:
                x_power += 1
            elif f.is_Pow and f.args[0] == X:
                # f = X^k
                x_power += int(f.args[1])
            else:
                # 곱셈 계수에 포함
                coeff_expr *= f

        return (coeff_expr, x_power)
    else:
        # 예) Add, 또는 다른 복잡한 형태
        # 보수적으로 처리: X 없는 경우 -> k=0, 있으면 나눠야 함
        free_symbols = sym_term.free_symbols
        if X in free_symbols:
            # (간단 예시는 여기 안 오도록 했으나, 혹시오면 최대치 추정)
            # 실제 현업 코드는 더 정교하게 분기해야 함
            # 여기서는 "X^1" 정도로 처리
            return (sym_term / X, 1)
        else:
            return (sym_term, 0)


##############################################################################
# 2) 확장된 LoopTransformer
##############################################################################
class ExtendedLoopTransformer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.required_k = set()

    def visit_FunctionDef(self, node):
        """
        함수 본문 전체 순회 후,
        - self.required_k (필요한 차수)만큼 progAvg_k 변수를 함수 초반부에 초기화
        """
        self.required_k.clear()
        self.generic_visit(node)

        # 필요한 progAvg_k 변수를 함수 시작 부분에 초기화
        init_stmts = []
        for k in sorted(self.required_k):
            init_stmts.append(
                ast.Assign(
                    targets=[ast.Name(id=f'progAvg_{k}', ctx=ast.Store())],
                    value=ast.Constant(value=0.0)  # Python3.8+; 이하 버전이면 ast.Num(...)
                )
            )

        node.body = init_stmts + node.body
        return node

    def visit_For(self, node):
        self.generic_visit(node)

        # for idx in range(len(x)) 확인
        if not (
            isinstance(node.target, ast.Name) and
            isinstance(node.iter, ast.Call) and
            isinstance(node.iter.func, ast.Name) and
            node.iter.func.id == 'range'
        ):
            return node

        args = node.iter.args
        if len(args) == 1:
            len_call = args[0]
        elif len(args) == 2:
            len_call = args[1]
        else:
            return node

        # len(x) 인지 확인
        if not (
            isinstance(len_call, ast.Call) and
            isinstance(len_call.func, ast.Name) and
            len_call.func.id == 'len' and
            len(len_call.args) == 1 and
            isinstance(len_call.args[0], ast.Name) and
            len_call.args[0].id == 'x'
        ):
            return node

        idx_name = node.target.id
        new_body = []

        for stmt in node.body:
            # 누적 += 식 찾기
            if (
                isinstance(stmt, ast.AugAssign) and
                isinstance(stmt.op, ast.Add) and
                isinstance(stmt.target, ast.Name) and
                isinstance(stmt.value, ast.AST)
            ):
                accum_var = stmt.target.id

                # Sympy 전개 -> {k: coefficient_expr(sympy)}
                poly_dict = parse_polynomial(stmt.value, idx_var_name=idx_name)
                # 필요한 차수 등록
                self.required_k.update(poly_dict.keys())

                # 1) 각 차수별 progAvg_k 업데이트
                #    progAvg_k = (idx*progAvg_k + coeff*k[x[idx]^k]) / (idx+1)
                #    여기서 coeff*k[x[idx]^k] = coeff * x[idx]^k
                #    (coeff는 ast 변환해서 곱해야 함)
                for k in sorted(poly_dict.keys()):
                    prog_var_name = f'progAvg_{k}'

                    # idx * progAvg_k
                    mul_part = ast.BinOp(
                        left=ast.Name(id=idx_name, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Name(id=prog_var_name, ctx=ast.Load())
                    )

                    # x[idx]^k
                    if k > 0:
                        x_sub = ast.Subscript(
                            value=ast.Name(id='x', ctx=ast.Load()),
                            slice=ast.Name(id=idx_name, ctx=ast.Load()),
                            ctx=ast.Load()
                        )
                        power_call = ast.Call(
                            func=ast.Name(id='pow', ctx=ast.Load()),
                            args=[x_sub, ast.Constant(value=k)],
                            keywords=[]
                        )
                        # coeff * x[idx]^k
                        coeff_ast = sympy_expr_to_ast(poly_dict[k])  # -2*average 등
                        right_expr = ast.BinOp(
                            left=coeff_ast,
                            op=ast.Mult(),
                            right=power_call
                        )
                    else:
                        # k=0 => x[idx]^0 = 1
                        coeff_ast = sympy_expr_to_ast(poly_dict[k])
                        right_expr = coeff_ast  # coeff_ast * 1

                    # (idx*progAvg_k + [coeff_ast * x[idx]^k])
                    plus_part = ast.BinOp(
                        left=mul_part,
                        op=ast.Add(),
                        right=right_expr
                    )

                    # denominator = (idx + 1)
                    denominator = ast.BinOp(
                        left=ast.Name(id=idx_name, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Constant(value=1)
                    )
                    update_expr = ast.BinOp(
                        left=plus_part,
                        op=ast.Div(),
                        right=denominator
                    )

                    assign_progavg_k = ast.Assign(
                        targets=[ast.Name(id=prog_var_name, ctx=ast.Store())],
                        value=update_expr
                    )
                    new_body.append(assign_progavg_k)

                # 2) 누적변수 accum_var = sum_{k} [ coeff_k * (len(x)*progAvg_k ) ] (for k>0)
                #                         + sum_{k=0} [ coeff_0 * len(x) ]  (if we assume each iteration adds that constant)
                #    => 실제로는 "k=0" 항도 len(x)*coeff_0 로 누적.
                len_x_call = ast.Call(
                    func=ast.Name(id='len', ctx=ast.Load()),
                    args=[ast.Name(id='x', ctx=ast.Load())],
                    keywords=[]
                )

                sum_expr = None
                for k in sorted(poly_dict.keys()):
                    coeff_ast = sympy_expr_to_ast(poly_dict[k])

                    if k == 0:
                        # k=0 항 => coeff_ast * len(x)
                        term_ast = ast.BinOp(
                            left=coeff_ast,
                            op=ast.Mult(),
                            right=len_x_call
                        )
                    else:
                        # k>0 => coeff_ast * len(x)*progAvg_k
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
                        sum_expr = ast.BinOp(
                            left=sum_expr,
                            op=ast.Add(),
                            right=term_ast
                        )

                if sum_expr is not None:
                    new_body.append(
                        ast.Assign(
                            targets=[ast.Name(id=accum_var, ctx=ast.Store())],
                            value=sum_expr
                        )
                    )
                else:
                    # poly_dict가 비어있을 때 (이상한 경우) -> 원본 유지
                    new_body.append(stmt)

            else:
                # 다른 구문은 그대로
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
    #print(ast.dump(new_tree, indent=4))
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
