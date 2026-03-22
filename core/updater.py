import json
import zipfile
import shutil
import urllib.request
import urllib.error
from pathlib import Path
import sys

# 본인 깃허브 레포로 교체
GITHUB_REPO = "paperface0128/OCE"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version() -> str:
    if getattr(sys, 'frozen', False):
        version_file = Path(sys.executable).parent / "version.json"
    else:
        version_file = Path(__file__).parent.parent / "version.json"
    
    if version_file.exists():
        try:
            with open(version_file, encoding="utf-8") as f:
                return json.load(f).get("version", "0.0.0")
        except Exception:
            pass
    
    # 없으면 exe 안에 묶인 버전 읽기
    try:
        if getattr(sys, 'frozen', False):
            bundled = Path(sys._MEIPASS) / "version.json"
        else:
            bundled = Path(__file__).parent.parent / "version.json"
        
        if bundled.exists():
            with open(bundled, encoding="utf-8") as f:
                version = json.load(f).get("version", "0.0.0")
            # exe 옆에 복사해서 다음부터 업데이트 가능하게
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump({"version": version}, f)
            return version
    except Exception:
        pass
    
    return "0.0.0"

def check_update() -> dict | None:
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={"User-Agent": "vn-editor-updater"}
        )
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read())

        latest = data.get("tag_name", "").lstrip("v")
        current = get_current_version()

        if _version_gt(latest, current):
            zip_url = None
            for asset in data.get("assets", []):
                if asset["name"] == "patch.zip":  # ← patch.zip만 인식
                    zip_url = asset["browser_download_url"]
                    break

            if not zip_url:
                return None

            body = data.get("body", "")
            is_force = "[FORCE]" in body.upper()
            notes = [line.strip("- ").strip()
                     for line in body.splitlines()
                     if line.strip().startswith("-")]

            return {
                "version": latest,
                "url": zip_url,
                "notes": notes,
                "force": is_force
            }
    except Exception:
        pass
    return None


def download_and_apply(zip_url: str, new_version: str,
                       progress_callback=None) -> bool:
    import tempfile
    import os
    import subprocess

    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.close()

        def reporthook(count, block_size, total_size):
            if total_size > 0 and progress_callback:
                percent = int(count * block_size * 100 / total_size)
                progress_callback(min(percent, 100))

        urllib.request.urlretrieve(zip_url, tmp.name, reporthook)

        if getattr(sys, 'frozen', False):
            pending_zip = base_dir / "patch_pending.zip"
            shutil.copy2(tmp.name, pending_zip)
            os.unlink(tmp.name)
            updater_exe = base_dir / "OCE_updater.exe"

            if updater_exe.exists():
                subprocess.Popen([
                    str(updater_exe),
                    str(pending_zip),
                    str(base_dir),
                    new_version,
                    str(sys.executable)
                ])
                return True
            else:
                return False
        else:
            # 개발 환경: 직접 적용
            with zipfile.ZipFile(tmp.name, "r") as zf:
                patch_path = next(
                    (n for n in zf.namelist() if n.endswith("patch.json")), None
                )
                if not patch_path:
                    return False

                prefix = patch_path.replace("patch.json", "")
                meta = json.loads(zf.read(patch_path))
                files = meta.get("files", [])

                for file_path in files:
                    if file_path == "patch.json":
                        continue
                    try:
                        dest = base_dir / file_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(prefix + file_path) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                    except Exception as e:
                        print(f"파일 교체 실패: {file_path} — {e}")

            with open(base_dir / "version.json", "w", encoding="utf-8") as f:
                json.dump({"version": new_version}, f)

            os.unlink(tmp.name)
            return True

    except Exception as e:
        print(f"업데이트 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def _version_gt(a: str, b: str) -> bool:
    """a > b 버전 비교"""
    try:
        return tuple(int(x) for x in a.split(".")) > \
               tuple(int(x) for x in b.split("."))
    except Exception:
        return False