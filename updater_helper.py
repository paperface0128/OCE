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

    log_path = target_dir / "updater_log.txt"

    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"=== OCE Updater 시작 ===\n")
        log.write(f"zip_path: {zip_path}\n")
        log.write(f"target_dir: {target_dir}\n")
        log.write(f"new_version: {new_version}\n")
        log.write(f"main_exe: {main_exe}\n\n")

        # 메인 앱 종료 대기
        log.write("2초 대기 중...\n")
        log.flush()
        time.sleep(2)

        try:
            log.write(f"zip 열기 시도: {zip_path}\n")
            log.flush()

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                log.write(f"zip 내용: {names}\n")

                patch_path = next(
                    (n for n in names if n.endswith("patch.json")), None
                )
                if not patch_path:
                    log.write("patch.json 없음 — 종료\n")
                    return

                prefix = patch_path.replace("patch.json", "")
                meta = json.loads(zf.read(patch_path))
                files = meta.get("files", [])
                log.write(f"교체할 파일: {files}\n\n")

                for file_path in files:
                    if file_path == "patch.json":
                        continue
                    try:
                        zip_entry = prefix + file_path
                        dest = target_dir / file_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(zip_entry) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        log.write(f"교체 완료: {file_path}\n")
                    except Exception as e:
                        log.write(f"교체 실패: {file_path} — {e}\n")
                    log.flush()

            # 버전 업데이트
            version_path = target_dir / "version.json"
            with open(version_path, "w", encoding="utf-8") as f:
                json.dump({"version": new_version}, f)
            log.write(f"\n버전 업데이트 완료: {new_version}\n")

            # 불필요한 assets 폴더 제거
            import shutil
            assets_path = target_dir / "assets"
            if assets_path.exists():
                shutil.rmtree(assets_path)
                log.write("assets 폴더 제거 완료\n")

            # zip 삭제
            try:
                os.unlink(zip_path)
                log.write("zip 삭제 완료\n")
            except Exception as e:
                log.write(f"zip 삭제 실패: {e}\n")

            # 메인 앱 재실행
            if main_exe and Path(main_exe).exists():
                import subprocess
                subprocess.Popen([main_exe])
                log.write(f"재실행: {main_exe}\n")
            else:
                log.write(f"재실행 실패: main_exe={main_exe}\n")

        except PermissionError as e:
            log.write(f"권한 오류: {e}\n")
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable,
                    " ".join(f'"{a}"' for a in sys.argv),
                    None, 1
                )
        except Exception as e:
            import traceback
            log.write(f"업데이트 실패: {e}\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()