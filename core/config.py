import json
import sys
from pathlib import Path


def _get_config_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "config.json"
    return Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    path = _get_config_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict):
    try:
        with open(_get_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"config 저장 실패: {e}")


def get_last_path() -> str | None:
    return load_config().get("last_path")


def set_last_path(path: str):
    cfg = load_config()
    cfg["last_path"] = path
    save_config(cfg)