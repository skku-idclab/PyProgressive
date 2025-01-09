import ast
import inspect
def func(x):
    sum = 0
    for i in x:
        sum += i
    return sum


def func2(x):
    sum = 0
    for i in range(0, len(x)):
        sum += x[i]
    
    return sum


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




source = inspect.getsource(func)
source2 = inspect.getsource(func2)
tree = ast.parse(source)
tree2 = ast.parse(source2)
print(source)

print()
print(ast.dump(tree, indent = 4))
print()
print(ast.dump(tree2, indent = 4))


#print(ast_to_list(tree))


