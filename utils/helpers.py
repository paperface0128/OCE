import re

BUTTON_COLORS = ["gray", "red", "green", "blurple"]
EMOTIONS = ["기본", "기쁨", "분노", "슬픔", "놀람", "수줍음"]
CONDITION_KEYS = ["flag", "stat", "equipped", "had", "time", "affection"]
STAT_KEYS = ["HP", "STR", "DEP", "INT", "WIS", "SPD", "REG", "FRD", "BOO"]


def is_valid_node_name(name: str) -> bool:
    """노드 이름 유효성 검사 (파일명으로 쓸 수 있는지)"""
    if not name:
        return False
    return bool(re.match(r'^[\w가-힣\-]+$', name))


def is_valid_expr(expr: str) -> bool:
    """조건식 유효성 검사 (>=10, <5 || >=30 등)"""
    if not expr:
        return False
    pattern = r'(>=|<=|==|!=|>|<)\s*\d+'
    parts = re.split(r'\|\||&&', expr)
    return all(re.fullmatch(r'\s*' + pattern + r'\s*', p) for p in parts)
