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
    

class LoopTransformer(ast.NodeTransformer):
    """
    1) for 루프에서:
       누적변수 += x[loop_index]
         -> 누적변수 = (누적변수 / (loop_index+1)) * len(x)
         -> 직후에 (바깥에서 삭제된) '어떤변수 = 누적변수 / len(x)' 의 '어떤변수'가 있다면
            -> '어떤변수 = 누적변수 / (loop_index+1)' 추가.

    2) for 바깥에서:
       어떤변수 = 다른변수 / len(x)
         -> 삭제 + '어떤변수'와 '다른변수'의 관계를 기록.
    """

    def __init__(self):
        super().__init__()
        # 바깥에서 "varA = varB / len(x)" 형태를 찾으면,
        #   self.div_map[varB] = varA
        # 로 기록한다.
        self.div_map = {}  # { dividendVarName : resultVarName }

    def visit_Assign(self, node):
        """
        바깥에서 'someVar = anotherVar / len(x)'를 찾으면
        -> (1) statement 삭제 (None 반환)
        -> (2) div_map[anotherVar] = someVar 로 기록
        """
        # 일단 하위 노드(=오른쪽 값 등)도 변환
        print("Assign visit")
        self.generic_visit(node)

        # node.targets: 할당받는 대상 (list)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assigned_var = node.targets[0].id  # 예: 'average'
            # 오른쪽 값이 BinOp( / )인지 확인
            rhs = node.value
            if (
                isinstance(rhs, ast.BinOp)
                and isinstance(rhs.op, ast.Div)
                # lhs of the division
                and isinstance(rhs.left, ast.Name)
                and isinstance(rhs.right, ast.Call)
                and isinstance(rhs.right.func, ast.Name)
                and rhs.right.func.id == 'len'
                and len(rhs.right.args) == 1
                and isinstance(rhs.right.args[0], ast.Name) 
                and rhs.right.args[0].id == 'x'
            ):
                # => "assigned_var = rhs.left / len(x)"
                dividend_var = rhs.left.id  # 예: 'accum'
                # 기록
                self.div_map[dividend_var] = assigned_var

                # statement 삭제
                return None

        return node
    
    def visit_For(self, node):
        """
        'for loopIndex in range(len(x))' 를 찾고,
        본문 중 'accumVar += x[loopIndex]' 패턴을
        -> accumVar = (accumVar / (loopIndex+1)) * len(x)
        로 바꾸고, 그 직후에 div_map[accumVar]가 있다면
        -> someVar = accumVar / (loopIndex+1)
        를 추가하는 로직.
        """
        print("Visit For")
        print("DEBUG Assign:", ast.dump(node))
        # 하위 노드(= for 내부 statements)도 먼저 방문해서 변환
        self.generic_visit(node)

        # 이 for문이 "for something in range(...)" 형태인지 확인
        if not isinstance(node.target, ast.Name):
            return node

        loop_index_name = node.target.id  # 예: idx, i 등

        if not isinstance(node.iter, ast.Call):
            return node
        if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != 'range':
            return node

        # range(...) 인자가 len(x)인지 간단 체크 (range(len(x)) 혹은 range(0, len(x)))
        args = node.iter.args
        if len(args) == 1:
            # range(len(x))
            len_call = args[0]
        elif len(args) == 2:
            # range(0, len(x))
            len_call = args[1]
        else:
            return node

        # len_call이 "len(x)" 형태인지?
        if not (
            isinstance(len_call, ast.Call)
            and isinstance(len_call.func, ast.Name)
            and len_call.func.id == 'len'
            and len(len_call.args) == 1
            and isinstance(len_call.args[0], ast.Name)
            and len_call.args[0].id == 'x'
        ):
            return node

        # 이제 body 내 statements에서 'accumVar += x[loop_index_name]' 찾기
        new_body = []
        for stmt in node.body:
            if (
                isinstance(stmt, ast.AugAssign)
                and isinstance(stmt.op, ast.Add)
                and isinstance(stmt.target, ast.Name)              # 누적변수
                and isinstance(stmt.value, ast.Subscript)          # x[something]
                and isinstance(stmt.value.value, ast.Name)
                and stmt.value.value.id == 'x'
            ):
                # 파이썬 3.9+ 에선 slice가 Index(...) 노드 안에 들어 있음
                slice_node = stmt.value.slice
                if isinstance(slice_node, ast.Index):  
                    slice_node = slice_node.value  # 실제 idx는 slice_node.value

                # slice_node가 ast.Name(...) 형태인지 확인
                if isinstance(slice_node, ast.Name) and slice_node.id == loop_index_name:
                    # 패턴 매칭 성공!
                    accum_var = stmt.target.id  # 예: accum

                    # 1) accumVar = (accumVar / (loopIndex+1)) * len(x)
                    left_div = ast.BinOp(
                        left=ast.Name(id=accum_var, ctx=ast.Load()),
                        op=ast.Div(),
                        right=ast.BinOp(
                            left=ast.Name(id=loop_index_name, ctx=ast.Load()),
                            op=ast.Add(),
                            right=ast.Constant(value=1)
                        )
                    )
                    len_x_call = ast.Call(
                        func=ast.Name(id='len', ctx=ast.Load()),
                        args=[ast.Name(id='x', ctx=ast.Load())],
                        keywords=[]
                    )
                    new_value = ast.BinOp(
                        left=left_div,
                        op=ast.Mult(),
                        right=len_x_call
                    )
                    new_assign_accum = ast.Assign(
                        targets=[ast.Name(id=accum_var, ctx=ast.Store())],
                        value=new_value
                    )
                    new_body.append(new_assign_accum)

                    # 2) 바깥(For 이전)에서 'someVar = accumVar / len(x)'가 삭제되었을 경우,
                    #    self.div_map[accum_var] = someVar 로 기록되어 있음.
                    #    => 'someVar = accumVar / (loopIndex+1)' 추가
                    if accum_var in self.div_map:
                        some_var = self.div_map[accum_var]
                        avg_value = ast.BinOp(
                            left=ast.Name(id=accum_var, ctx=ast.Load()),
                            op=ast.Div(),
                            right=ast.BinOp(
                                left=ast.Name(id=loop_index_name, ctx=ast.Load()),
                                op=ast.Add(),
                                right=ast.Constant(value=1)
                            )
                        )
                        new_assign_avg = ast.Assign(
                            targets=[ast.Name(id=some_var, ctx=ast.Store())],
                            value=avg_value
                        )
                        new_body.append(new_assign_avg)
                else:
                    # slice가 우리가 원하는 형태가 아님 => 변환하지 않고 그대로
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
        if not line.strip().startswith('@')
    ]
    new_source = '\n'.join(filtered_lines)

    print(new_source)

    # 1) AST 파싱
    tree = ast.parse(new_source)
    print(ast.dump(tree, indent=4))
    # 2) NodeTransformer 적용
    transformer = LoopTransformer()
    print("visit start")
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    print(ast.dump(new_tree, indent=4))

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




