import hashlib
import json
from pathlib import Path
from core.models import Project


def validate_project(project: Project) -> list[str]:
    """저장 전 경고 (비치명적)"""
    warnings = []

    if not project.meta.name.strip():
        warnings.append("캐릭터 이름이 비어있습니다.")

    node_names = project.node_names()
    if "_START" not in node_names:
        warnings.append("_START 노드가 없습니다.")

    for node in project.nodes:
        if not node.dialogues:
            warnings.append(f"노드 [{node.name}]에 대사가 없습니다.")
            continue
        for dlg in node.dialogues:
            if not dlg.id.strip():
                warnings.append(f"노드 [{node.name}]에 ID가 없는 대사가 있습니다.")
            if not dlg.steps:
                warnings.append(f"대사 [{dlg.id}]에 스텝이 없습니다.")
        for btn in node.buttons:
            if btn.next and btn.next not in node_names:
                warnings.append(
                    f"버튼 [{btn.id}]의 next 노드 [{btn.next}]가 존재하지 않습니다."
                )

    return warnings

def compute_integrity(project: Project) -> dict[str, str]:
    """각 노드의 해시값 계산 (무결성 기준값)"""
    result = {}
    for node in project.nodes:
        data = json.dumps(node.to_dict(), ensure_ascii=False, sort_keys=True)
        result[node.name] = hashlib.sha256(data.encode()).hexdigest()
    return result


def verify_integrity(project: Project, saved_path: str) -> list[str]:
    warnings = []
    if not saved_path:
        return warnings

    base = Path(saved_path)
    scripts_path = base / "scripts"

    if not scripts_path.exists():
        return warnings

    for node in project.nodes:
        file_path = scripts_path / f"{node.name}.json"
        if not file_path.exists():
            continue
        try:
            with open(file_path, encoding="utf-8") as f:
                saved_data = json.load(f)
            saved_hash = hashlib.sha256(
                json.dumps(saved_data, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            current_data = node.to_dict()
            current_hash = hashlib.sha256(
                json.dumps(current_data, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            # if saved_hash != current_hash:
            #     # 디버그용
            #     print(f"[{node.name}] 불일치!")
            #     print(f"저장: {json.dumps(saved_data, ensure_ascii=False)}")
            #     print(f"현재: {json.dumps(current_data, ensure_ascii=False)}")
            #     warnings.append(f"[{node.name}]")
        except Exception:
            pass

    return warnings

def _conditions_can_coexist(cond_a: dict, cond_b: dict) -> bool:
    """두 조건이 동시에 만족될 수 있는지 확인"""

    def parse_op_val(expr: str):
        """'>=100' → ('>=', 100)"""
        for op in [">=", "<=", ">", "<", "==", "!="]:
            if expr.startswith(op):
                try:
                    return op, int(expr[len(op):])
                except ValueError:
                    return None, None
        return None, None

    def ranges_overlap(expr_a: str, expr_b: str) -> bool:
        """두 수치 조건이 겹치는 범위가 있는지"""
        op_a, val_a = parse_op_val(expr_a)
        op_b, val_b = parse_op_val(expr_b)
        if None in (op_a, val_a, op_b, val_b):
            return True  # 파싱 불가 → 보수적으로 겹친다고 가정

        # 각 조건을 (min, max) 범위로 변환
        INF = float('inf')

        def to_range(op, val):
            if op == ">=": return (val, INF)
            if op == ">":  return (val + 1, INF)
            if op == "<=": return (-INF, val)
            if op == "<":  return (-INF, val - 1)
            if op == "==": return (val, val)
            if op == "!=": return None  # 복잡, 보수적으로 처리
            return (-INF, INF)

        r_a = to_range(op_a, val_a)
        r_b = to_range(op_b, val_b)
        if r_a is None or r_b is None:
            return True  # 보수적으로 겹친다고 가정

        # 범위 겹침 확인
        return r_a[0] <= r_b[1] and r_b[0] <= r_a[1]

    # ── affection 비교 ──
    aff_a = cond_a.get("affection", ">=0")
    aff_b = cond_b.get("affection", ">=0")
    if not ranges_overlap(aff_a, aff_b):
        return False

    # ── flag 비교 ──
    flags_a = cond_a.get("flag", {})
    flags_b = cond_b.get("flag", {})
    for flag_key in set(flags_a) | set(flags_b):
        if flag_key in flags_a and flag_key in flags_b:
            if not ranges_overlap(flags_a[flag_key], flags_b[flag_key]):
                return False

    # ── stat 비교 ──
    stat_a = cond_a.get("stat", {})
    stat_b = cond_b.get("stat", {})
    for stat_key in set(stat_a) | set(stat_b):
        if stat_key in stat_a and stat_key in stat_b:
            if not ranges_overlap(stat_a[stat_key], stat_b[stat_key]):
                return False

    # ── equipped 비교 ──
    # equipped 는 "이 장비를 착용 중이어야 함"
    # 서로 다른 장비를 요구하면서 AND 로 묶이면 불가능할 수도 있지만
    # equipped 는 여러 개 착용 가능하므로 보수적으로 겹친다고 가정
    # (equipped:[] 는 조건 없음)

    return True


def _max_concurrent_buttons(buttons: list) -> int:
    """최악의 경우 동시에 나올 수 있는 최대 버튼 수 계산"""
    if not buttons:
        return 0

    # 조건 없는 버튼은 항상 나옴
    always_visible = [b for b in buttons if not b.conditions]
    conditional = [b for b in buttons if b.conditions]

    # 조건 있는 버튼들 중 서로 공존 가능한 최대 그룹 크기 계산
    # 그리디: 가장 많이 공존 가능한 버튼 세트 찾기
    max_conditional = 0
    n = len(conditional)

    # 비트마스크로 모든 부분집합 검사 (버튼 수가 적을 때)
    if n <= 15:
        for mask in range(1, 1 << n):
            group = [conditional[i] for i in range(n) if mask & (1 << i)]
            # 이 그룹의 모든 쌍이 공존 가능한지
            can_coexist = True
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    if not _conditions_can_coexist(group[i].conditions, group[j].conditions):
                        can_coexist = False
                        break
                if not can_coexist:
                    break
            if can_coexist:
                max_conditional = max(max_conditional, len(group))
    else:
        # 버튼이 너무 많으면 보수적으로 전체 수 반환
        max_conditional = n

    return len(always_visible) + max_conditional


def check_project(project: Project) -> list[str]:
    """적법성 검사 (치명적 — 저장 불가)"""
    errors = []
    node_names = project.node_names()
    node_map = {n.name: n for n in project.nodes}

    # ── 버튼 동시 출현 5개 초과 검사 ──
    for node in project.nodes:
        max_visible = _max_concurrent_buttons(node.buttons)
        if max_visible > 5:
            errors.append(
                f"노드 [{node.name}]: 동시에 표시될 수 있는 버튼이 최대 {max_visible}개입니다. "
                f"디스코드는 최대 5개까지 허용합니다."
            )

    # ── 적어도 하나의 루트로 끝낼 수 있는지 검사 ──
    def has_any_terminal_path(node_name: str, visited: set) -> bool:
        """이 노드에서 시작해서 적어도 하나의 경로로 끝 노드에 도달 가능한가"""
        if node_name in visited:
            return False
        if node_name not in node_map:
            return False
        node = node_map[node_name]
        if not node.buttons:
            return True  # 끝 노드
        visited = visited | {node_name}
        # any: 하나의 버튼이라도 끝에 도달하면 OK
        return any(
            has_any_terminal_path(btn.next, visited)
            for btn in node.buttons
            if btn.next and btn.next in node_map
        )

    for node in project.nodes:
        if node.buttons:
            if not has_any_terminal_path(node.name, set()):
                errors.append(
                    f"노드 [{node.name}]: 어떤 경로로도 대화를 끝낼 수 없습니다. "
                    f"버튼 없는 노드로 이어지는 경로가 하나도 없습니다."
                )

    # ── 연결되지 않은 버튼 next 검사 ──
    for node in project.nodes:
        for btn in node.buttons:
            if btn.next and btn.next not in node_names:
                errors.append(
                    f"노드 [{node.name}] 버튼 [{btn.label or btn.id}]: "
                    f"연결된 노드 [{btn.next}]가 존재하지 않습니다."
                )

    return errors