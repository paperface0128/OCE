from pathlib import Path
import customtkinter as ctk
from PIL import Image

_cache: dict = {}

ICON_DIR = Path(__file__).parent.parent / "assets" / "icons"

_BASE_DIR = Path(__file__).parent.parent

def _set_base_dir(path: str):
    global _BASE_DIR, ICON_DIR
    _BASE_DIR = Path(path)
    ICON_DIR = _BASE_DIR / "assets" / "icons"
    
def get_icon(name: str, size: int = 18) -> ctk.CTkImage | None:
    """아이콘 이름으로 CTkImage 반환. 파일 없으면 None"""
    key = (name, size)
    if key in _cache:
        return _cache[key]

    path = ICON_DIR / f"{name}.png"
    if not path.exists():
        return None

    try:
        img = Image.open(path).convert("RGBA")
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        _cache[key] = ctk_img
        return ctk_img
    except Exception as e:
        print(f"아이콘 로드 실패: {name} — {e}")
        return None


def btn(parent, text: str, icon_name: str = None, size: int = 18, **kwargs):
    """아이콘 + 텍스트 버튼 생성 헬퍼"""
    icon = get_icon(icon_name, size) if icon_name else None
    return ctk.CTkButton(
        parent,
        text=text,
        image=icon,
        compound="left" if icon else "center",
        **kwargs
    )