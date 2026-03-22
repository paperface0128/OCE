from pathlib import Path
from typing import Optional
import customtkinter as ctk

_item_icons: dict = {}
_gear_icons: dict = {}
_default_icon = None
_loaded = False


def preload_icons(base_path: str):
    """앱 시작 시 호출 — 아이템/장비 아이콘 미리 로딩"""
    global _loaded, _default_icon
    if _loaded:
        return

    try:
        from PIL import Image
    except ImportError:
        return

    base = Path(base_path)

    # 기본 아이콘 (이미지 없을 때)
    try:
        blank = Image.new("RGBA", (32, 32), (60, 60, 60, 255))
        _default_icon = ctk.CTkImage(light_image=blank, dark_image=blank, size=(24, 24))
    except Exception:
        pass

    # 아이템 아이콘
    items_dir = base / "assets" / "items"
    if items_dir.exists():
        for img_path in items_dir.glob("*.png"):
            try:
                item_id = int(img_path.stem)
                img = Image.open(img_path).convert("RGBA")
                icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
                _item_icons[item_id] = icon
            except Exception:
                pass

    # 장비 아이콘
    gears_dir = base / "assets" / "gears"
    if gears_dir.exists():
        for img_path in gears_dir.glob("*.png"):
            try:
                gear_id = int(img_path.stem)
                img = Image.open(img_path).convert("RGBA")
                icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
                _gear_icons[gear_id] = icon
            except Exception:
                pass

    _loaded = True


def get_item_icon(item_id: int):
    return _item_icons.get(item_id, _default_icon)


def get_gear_icon(gear_id: int):
    return _gear_icons.get(gear_id, _default_icon)