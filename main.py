import sys
import os
from pathlib import Path
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
# exe 빌드 시 내부 경로, 개발 시 현재 경로
if getattr(sys, 'frozen', False):
    base_dir = Path(sys._MEIPASS)
    # 설정/저장 파일은 exe 옆에
    work_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent
    work_dir = base_dir

os.chdir(work_dir)

# DB 경로 설정
from core.db_reader import set_db_path
set_db_path(str(base_dir / "assets" / "data" / "static.db"))

# 아이콘 미리 로딩
from core import icon_cache
icon_cache.preload_icons(str(base_dir))

from core.db_reader import get_item_options, get_gear_options
get_item_options()
get_gear_options()

from utils.icons import _set_base_dir
_set_base_dir(str(base_dir))

from ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()