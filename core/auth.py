import urllib.request
import urllib.parse
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

SERVER_URL = "https://complete-kari-paperface0128-a98e1fcc.koyeb.app"  # ← Koyeb URL로 교체
TOOL_SECRET = "PAPERFACEISSEXY"  # ← 봇 환경변수 TOOL_SECRET 과 동일하게
REDIRECT_URI_TOOL = "http://localhost:8765/callback"


_auth_result: dict = {}
_auth_event: threading.Event = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]

        # 브라우저에 완료 페이지 표시
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write((
            "<html><head><meta charset='utf-8'></head>"
            "<body style='background:#1a1a2e;color:white;font-family:sans-serif;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'>"
            "<h2>✅ 인증 완료!</h2>"
            "<p>이 창을 닫고 툴로 돌아가세요.</p>"
            "</div>"
            "<script>setTimeout(()=>window.close(), 2000);</script>"
            "</body></html>"
        ).encode("utf-8"))

        if code:
            _auth_result["code"] = code
        _auth_event.set()

    def log_message(self, format, *args):
        pass


def login_with_discord(on_complete=None, on_error=None):
    """
    비동기로 디스코드 로그인 진행
    on_complete(auth: dict) — 성공 시 호출
    on_error(msg: str) — 실패 시 호출
    """
    def _run():
        global _auth_result, _auth_event
        _auth_result = {}
        _auth_event = threading.Event()

        try:
            # 로컬 콜백 서버 시작
            server = HTTPServer(("localhost", 8765), _CallbackHandler)
            t = threading.Thread(target=server.handle_request, daemon=True)
            t.start()

            # 브라우저로 인증 URL 열기
            webbrowser.open(f"{SERVER_URL}/api/auth/start")

            # 콜백 대기 (최대 120초)
            if not _auth_event.wait(timeout=120):
                server.server_close()
                if on_error:
                    on_error("인증 시간이 초과되었습니다.")
                return

            server.server_close()
            code = _auth_result.get("code")
            if not code:
                if on_error:
                    on_error("인증 코드를 받지 못했습니다.")
                return

            # 서버에 코드 전달 → user_id 받기
            callback_url = (
                f"{SERVER_URL}/callback"
                f"?code={urllib.parse.quote(code)}&state=tool"
            )
            with urllib.request.urlopen(callback_url, timeout=15) as resp:
                result = resp.read().decode().strip()

            if not result.startswith("ok:"):
                if on_error:
                    on_error(f"인증 실패: {result}")
                return

            user_id = result.split(":", 1)[1].strip()

            # 플랜 확인
            plan_url = (
                f"{SERVER_URL}/api/plan"
                f"?user_id={user_id}&secret={TOOL_SECRET}"
            )
            with urllib.request.urlopen(plan_url, timeout=10) as resp:
                plan_data = json.loads(resp.read())

            auth = {
                "user_id": user_id,
                "plan": plan_data.get("plan", "free")
            }

            # 저장
            save_auth(auth)

            if on_complete:
                on_complete(auth)

        except Exception as e:
            if on_error:
                on_error(str(e))

    threading.Thread(target=_run, daemon=True).start()


def refresh_plan(user_id: str) -> str:
    """저장된 user_id 로 플랜 재확인"""
    try:
        plan_url = (
            f"{SERVER_URL}/api/plan"
            f"?user_id={user_id}&secret={TOOL_SECRET}"
        )
        with urllib.request.urlopen(plan_url, timeout=10) as resp:
            plan_data = json.loads(resp.read())
        return plan_data.get("plan", "free")
    except Exception:
        return "free"


def get_saved_auth() -> dict | None:
    """저장된 인증 정보 불러오기"""
    auth_path = _get_auth_path()
    if auth_path.exists():
        try:
            with open(auth_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_auth(auth: dict):
    """user_id 만 저장 — plan 은 저장 안 함"""
    try:
        data = {"user_id": auth["user_id"]}  # plan 제외
        with open(_get_auth_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"인증 저장 실패: {e}")


def clear_auth():
    """로그아웃"""
    try:
        _get_auth_path().unlink(missing_ok=True)
    except Exception:
        pass


def _get_auth_path() -> Path:
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "auth.json"
    return Path(__file__).parent.parent / "auth.json"