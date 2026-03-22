import sys
import os
import time
import zipfile
import json
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        return

    zip_path = sys.argv[1]
    target_dir = Path(sys.argv[2])
    new_version = sys.argv[3] if len(sys.argv) > 3 else "0.0.0"
    main_exe = sys.argv[4] if len(sys.argv) > 4 else None

    # 메인 앱 종료 대기
    time.sleep(2)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            patch_path = next(
                (n for n in zf.namelist() if n.endswith("patch.json")), None
            )
            if not patch_path:
                print("patch.json 없음")
                return

            prefix = patch_path.replace("patch.json", "")
            meta = json.loads(zf.read(patch_path))
            files = meta.get("files", [])

            for file_path in files:
                if file_path == "patch.json":
                    continue
                try:
                    zip_entry = prefix + file_path
                    dest = target_dir / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(zip_entry) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
                    print(f"교체 완료: {file_path}")
                except Exception as e:
                    print(f"실패: {file_path} — {e}")

        # 버전 업데이트
        version_path = target_dir / "version.json"
        with open(version_path, "w", encoding="utf-8") as f:
            json.dump({"version": new_version}, f)
        print(f"버전 업데이트: {new_version}")

        # 불필요한 assets 폴더 제거 (이제 exe 안에 묶임)
        import shutil
        assets_path = target_dir / "assets"
        if assets_path.exists():
            shutil.rmtree(assets_path)
            print("불필요한 assets 폴더 제거 완료")

        try:
            os.unlink(zip_path)
        except Exception:
            pass


    except PermissionError as e:
        print(f"권한 오류: {e}")
        # 관리자 권한으로 재실행
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                " ".join(f'"{a}"' for a in sys.argv),
                None, 1
            )
    except Exception as e:
        print(f"업데이트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()