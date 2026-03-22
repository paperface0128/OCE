import sqlite3
from pathlib import Path
from typing import Optional

_DB_PATH: Optional[Path] = None
_items_cache: list = []
_gears_cache: list = []
_all_gears_cache: list = []
_item_options: list[str] = []
_gear_options: list[str] = []
_loaded: bool = False


def set_db_path(path: str):
    global _DB_PATH
    _DB_PATH = Path(path)


def _load():
    global _items_cache, _gears_cache, _all_gears_cache, _item_options, _gear_options, _loaded
    if _loaded or not _DB_PATH or not _DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT ID, 이름 FROM 아이템 WHERE 자만툴 = 1 ORDER BY ID")
        _items_cache = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        _item_options = [f"{i['id']}. {i['name']}" for i in _items_cache]

        cursor.execute("SELECT ID, 이름, 유형 FROM 장비 WHERE 자만툴 = 1 ORDER BY ID")
        _gears_cache = [{"id": row[0], "name": row[1], "type": row[2]} for row in cursor.fetchall()]
        _gear_options = [f"{g['id']}. {g['name']}" for g in _gears_cache]

        cursor.execute("SELECT ID, 이름, 유형 FROM 장비 ORDER BY ID")
        _all_gears_cache = [{"id": row[0], "name": row[1], "type": row[2]} for row in cursor.fetchall()]

        conn.close()
        _loaded = True
        print(f"DB 로드 완료: 아이템 {len(_items_cache)}개, 장비 {len(_gears_cache)}개 (전체 {len(_all_gears_cache)}개)")
    except Exception as e:
        print(f"DB 로드 실패: {e}")
        import traceback
        traceback.print_exc()


def get_items() -> list:
    _load()
    return _items_cache

def get_item_options() -> list[str]:
    _load()
    return _item_options

def get_gears() -> list:
    _load()
    return _gears_cache

def get_gear_options() -> list[str]:
    _load()
    return _gear_options

def get_all_gears() -> list:
    """자만툴 값 상관없이 전체 장비 반환"""
    _load()
    return _all_gears_cache