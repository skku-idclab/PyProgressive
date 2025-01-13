import ast
import inspect
import copy
import dill

def ast_to_list(node):
    """
    주어진 AST 노드를, (노드_이름, [자식_노드들]) 형태의
    중첩 리스트로 변환하는 예시 함수.
    """
    # 노드 클래스 이름
    node_type = type(node).__name__
    
    # 자식 노드들을 재귀적으로 변환
    children = []
    
    # node._fields를 순회하면, 해당 노드가 가진 속성(필드)들을 알 수 있음
    for field_name in node._fields:
        field_value = getattr(node, field_name, None)

        if isinstance(field_value, list):
            # 예: body=[Stmt1, Stmt2, ...] 처럼 리스트인 경우
            child_list = []
            for item in field_value:
                if isinstance(item, ast.AST):
                    child_list.append(ast_to_list(item))
                else:
                    # 상수나 문자열일 수도 있음
                    child_list.append(item)
            children.append((field_name, child_list))

        elif isinstance(field_value, ast.AST):
            # 단일 AST 노드
            children.append((field_name, ast_to_list(field_value)))

        else:
            # int, str 등의 단순 속성
            children.append((field_name, field_value))

    return [node_type, children]

def list_to_ast(node_list):
    """
    '[노드이름, [(필드이름, 값), (필드이름, 값), ...]]' 형태의 리스트를
    재귀적으로 ast 노드 객체로 복원한다.
    """
    # node_list: ["Module" (또는 "FunctionDef" 등), [ (field_name, field_val), ... ] ]
    node_type = node_list[0]
    children = node_list[1]

    # ast 모듈에서 해당 node_type에 대응하는 클래스를 가져옴 (예: "Module" -> ast.Module)
    node_class = getattr(ast, node_type, None)
    if node_class is None:
        # 만약 ast에 없는 클래스면, 여기서는 단순히 None 반환하거나 에러를 낸다
        raise ValueError(f"Unknown AST node type: {node_type}")

    # 해당 노드 클래스의 객체를 우선 생성 (예: node_obj = ast.Module())
    # 나중에 필드를 setattr로 채워 넣을 것이다.
    node_obj = node_class()

    # children은 [(field_name, field_val), ...] 형태
    for (field_name, field_val) in children:
        # field_val을 재귀적으로 파싱
        parsed_val = from_list_value(field_val)
        setattr(node_obj, field_name, parsed_val)

    return node_obj


def from_list_value(val):
    """
    list_to_ast에 사용되는 헬퍼 함수.
    - 만약 val이 [node_type, [...]] 형태라면 단일 AST 노드로 변환.
    - 만약 val이 list이지만 여러 항목이 있다면, 각각을 재귀적으로 처리.
    - 그렇지 않으면(숫자, 문자열, None 등)이면 그대로 반환.
    """
    # 1) 만약 val이 리스트인데,
    if isinstance(val, list):
        # 예) ["Module", [...]] or ["Name", [...]] 등등
        # "AST 노드 한 개"일 수도 있고, "AST 노드 여러 개를 담은 리스트"일 수도 있음
        if len(val) == 2 and isinstance(val[0], str) and isinstance(val[1], list):
            # '[노드이름, [(필드명, 필드값), ...]]' 형태라고 가정 -> 단일 노드
            return list_to_ast(val)  # 재귀 호출
        else:
            # 그렇지 않다면, list의 각 item을 순회하며 처리 (ex. body, targets 등)
            new_list = []
            for item in val:
                new_list.append(from_list_value(item))
            return new_list
    else:
        # 2) list가 아니라면 (int, str, None, bool 등) 그대로 반환
        return val
    

import ast

class LoopTransformer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        # 필요하다면 다른 속성도 넣을 수 있음
        # 예: self.div_map = {}

    def visit_FunctionDef(self, node):
        """
        (1) 함수 내부에서 'progAvg' 변수가 선언(할당)되지 않았다면,
            맨 앞에 'progAvg = 0.0' 문을 삽입.
        (2) 그 뒤, 함수 본문을 하위 노드까지 탐색 (self.generic_visit).
        """

        # 먼저 자식 노드(For, Assign 등) 방문
        self.generic_visit(node)

        # 함수 내부에 이미 'progAvg = ...' 할당문이 있는지 확인
        declared_progavg = False
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == 'progAvg'
            ):
                # "progAvg = ..." 할당 발견
                declared_progavg = True
                break

        if not declared_progavg:
            # 함수 몸체 맨 앞에 "progAvg = 0.0" 삽입
            init_progavg = ast.Assign(
                targets=[ast.Name(id='progAvg', ctx=ast.Store())],
                value=ast.Constant(value=0.0)
            )
            node.body.insert(0, init_progavg)

        return node

    def visit_For(self, node):
        """
        (1) 'for idx in range(len(x)):' 형태 확인.
        (2) 본문에서 'accum += x[idx]'를 찾으면,
            progAvg = (idx * progAvg + x[idx]) / (idx + 1)
            accum   = progAvg * len(x)
            두 줄로 치환.
        """

        # 하위 노드(For 내부 statements)도 먼저 방문
        self.generic_visit(node)

        # 이 For 문이 "for idx in range(len(x))" 형태인지 간단 체크
        if not isinstance(node.target, ast.Name):
            return node
        loop_index_name = node.target.id  # 예: 'idx' or 'i'

        if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range'):
            return node

        args = node.iter.args
        if len(args) == 1:
            # range(len(x))
            len_call = args[0]
        elif len(args) == 2:
            # range(0, len(x))
            len_call = args[1]
        else:
            return node

        # len_call이 "len(x)" 형태인지
        if not (
            isinstance(len_call, ast.Call)
            and isinstance(len_call.func, ast.Name)
            and len_call.func.id == 'len'
            and len(len_call.args) == 1
            and isinstance(len_call.args[0], ast.Name)
            and len_call.args[0].id == 'x'
        ):
            return node

        new_body = []
        for stmt in node.body:
            # 패턴 매칭: accum += x[idx]
            if (
                isinstance(stmt, ast.AugAssign)
                and isinstance(stmt.op, ast.Add)
                and isinstance(stmt.target, ast.Name)         # accum
                and isinstance(stmt.value, ast.Subscript)     # x[something]
                and isinstance(stmt.value.value, ast.Name)
                and stmt.value.value.id == 'x'
            ):
                slice_node = stmt.value.slice
                # Python 3.9+ 에서 x[idx] -> Subscript(slice=Index(value=Name('idx')))
                if isinstance(slice_node, ast.Index):
                    slice_node = slice_node.value

                if isinstance(slice_node, ast.Name) and slice_node.id == loop_index_name:
                    accum_var = stmt.target.id  # 예: 'accum'

                    # ----------------------------
                    # 1) progAvg = (idx * progAvg + x[idx]) / (idx + 1)
                    # ----------------------------
                    # (idx * progAvg)
                    idx_times_progavg = ast.BinOp(
                        left=ast.Name(id=loop_index_name, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Name(id='progAvg', ctx=ast.Load())
                    )
                    # (idx * progAvg + x[idx])
                    sum_expr = ast.BinOp(
                        left=idx_times_progavg,
                        op=ast.Add(),
                        right=ast.Subscript(
                            value=ast.Name(id='x', ctx=ast.Load()),
                            slice=ast.Name(id=loop_index_name, ctx=ast.Load()),
                            ctx=ast.Load()
                        )
                    )
                    # denominator = (idx + 1)
                    denominator = ast.BinOp(
                        left=ast.Name(id=loop_index_name, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Constant(value=1)
                    )
                    # (idx*progAvg + x[idx]) / (idx+1)
                    progavg_value = ast.BinOp(
                        left=sum_expr,
                        op=ast.Div(),
                        right=denominator
                    )
                    new_assign_progavg = ast.Assign(
                        targets=[ast.Name(id='progAvg', ctx=ast.Store())],
                        value=progavg_value
                    )

                    # ----------------------------
                    # 2) accum = progAvg * len(x)
                    # ----------------------------
                    len_x_call = ast.Call(
                        func=ast.Name(id='len', ctx=ast.Load()),
                        args=[ast.Name(id='x', ctx=ast.Load())],
                        keywords=[]
                    )
                    accum_value = ast.BinOp(
                        left=ast.Name(id='progAvg', ctx=ast.Load()),
                        op=ast.Mult(),
                        right=len_x_call
                    )
                    new_assign_accum = ast.Assign(
                        targets=[ast.Name(id=accum_var, ctx=ast.Store())],
                        value=accum_value
                    )

                    # 이 두 줄을 바디에 추가
                    new_body.append(new_assign_progavg)
                    new_body.append(new_assign_accum)

                else:
                    # slice가 우리가 원하는 idx 아님 -> 그대로 유지
                    new_body.append(stmt)

            else:
                # 다른 구문은 그대로
                new_body.append(stmt)

        node.body = new_body
        return node


    


def transform_decorator(func):
    """
    주어진 함수 `func`를 소스코드 -> AST 파싱 -> 변환 -> 재컴파일 -> 새 함수로 만드는 데코레이터.
    """
    if getattr(func, '__transformed__', False):
        return func

    source = inspect.getsource(func)

    

    lines = source.split('\n')
    filtered_lines = [
        line
        for line in lines
        if not line.strip().startswith('@PyProgress')
    ]
    new_source = '\n'.join(filtered_lines)


    # 1) AST 파싱
    tree = ast.parse(new_source)
    #print(ast.dump(tree, indent=4))
    # 2) NodeTransformer 적용
    transformer = LoopTransformer()
    print("visit start")
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    #print(ast.dump(new_tree, indent=4))

    # 3) compile -> exec
    code = compile(new_tree, filename="<ast-transform>", mode="exec")
    new_globals = copy.copy(func.__globals__)
    exec(code, new_globals)

    # 4) 새로 만들어진 함수 객체 추출
    transformed_func = new_globals[func.__name__]
    # 메타데이터 복사
    transformed_func.__name__ = func.__name__
    transformed_func.__doc__ = func.__doc__
    transformed_func.__module__ = func.__module__

    transformed_func.__transformed__ = True

    return transformed_func




