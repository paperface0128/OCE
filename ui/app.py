import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from core.models import Project, Node
from core.project import new_project, load_project, save_project
from core.validator import validate_project
from utils.icons import get_icon, btn

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        from core.updater import get_current_version
        version = get_current_version()
        self.title(f"자만툴 v{version}")
        self.geometry("1280x720")
        self.minsize(900, 600)

        self.project: Project = new_project()
        self._selected_node: str | None = "_START"

        self._build_layout()
        self._refresh_node_list()
        self._load_node("_START")
        self.after(500, self._run_checks)
        self._is_loading = False

        self.after(2000, self._check_update)  # 앱 로드 후 2초 뒤 체크
        self.after(100, self._load_last_project)
    def _load_last_project(self):
        from core.config import get_last_path
        from core.project import load_project
        last = get_last_path()
        if not last:
            return
        from pathlib import Path
        if not Path(last).exists():
            return
        try:
            project = load_project(last)
        except Exception:
            return

        def _do():
            self._is_loading = True
            self.project = project
            self._selected_node = "_START"
            self.meta_page.load_meta(self.project.meta, is_saved=True)
            self._refresh_node_list()
            self.node_page.load_node(
                self.project.get_node("_START"),
                self.project.node_names()
            )
            self.tabview.set("노드 편집")
            self.title_label.configure(text=self.project.meta.name or "캐릭터")
            def _finish():
                self._is_loading = False
                self._run_checks()
            self.after(800, _finish)

        self._show_full_loading(_do)
    def _check_update(self):
        import threading
        def run():
            from core.updater import check_update
            info = check_update()
            if info:
                self.after(0, lambda: self._show_update_dialog(info))
        threading.Thread(target=run, daemon=True).start()

    def _show_update_dialog(self, info: dict):
        from ui.components.update_dialog import UpdateDialog
        UpdateDialog(self, info)
    # ─────────────────────────────────────────
    # 레이아웃 구성
    # ─────────────────────────────────────────
    def _build_layout(self):
        self.toolbar = ctk.CTkFrame(self, height=48, corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self._build_toolbar()

        # 상태바 (툴바 아래)
        from ui.components.status_bar import StatusBar
        self.status_bar = StatusBar(self, fg_color="#111111")
        self.status_bar.pack(fill="x", side="top")

        self.body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(self.body, width=200, corner_radius=0)
        self.sidebar.pack(fill="y", side="left", padx=(0, 1))
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.content = ctk.CTkFrame(self.body, corner_radius=0, fg_color="transparent")
        self.content.pack(fill="both", expand=True)
        self._build_tabs()

    def _build_toolbar(self):
        btn_cfg = dict(height=32, corner_radius=6)

        ctk.CTkButton(self.toolbar, text="새 프로젝트", image=get_icon("plus"), **btn_cfg,
                      command=self._new_project).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(self.toolbar, text="불러오기", image=get_icon("save"), **btn_cfg,
                      command=self._open_project).pack(side="left", padx=2, pady=8)
        ctk.CTkButton(self.toolbar, text="저장", image=get_icon("saveas"), **btn_cfg,width=80,
                      fg_color="#2d7a3a", hover_color="#235e2c",
                      command=self._save_project).pack(side="left", padx=2, pady=8)
        ctk.CTkButton(self.toolbar, text="다른 이름으로 저장", image=get_icon("saveas"), **btn_cfg,
                      fg_color="#2d7a3a", hover_color="#235e2c",
                      command=self._save_as_project).pack(side="left", padx=2, pady=8)
        # ← 여기 로그인 버튼
        self._login_btn = ctk.CTkButton(
            self.toolbar, image=get_icon("discord"), text="로그인", height=32, width=100,
            corner_radius=6,
            fg_color="#5865F2", hover_color="#4752c4",
            command=self._handle_login
        )
        self._login_btn.pack(side="left", padx=6, pady=8)

        ctk.CTkButton(self.toolbar, text="크레딧", image=get_icon("credit"), **btn_cfg,
                      fg_color="transparent", hover_color="#2a2a2a",
                      command=self._show_credits).pack(side="left", padx=0, pady=8)
        ctk.CTkButton(self.toolbar, text="후원하기", image=get_icon("donate"), **btn_cfg,
                      fg_color="transparent", hover_color="#2a2a2a",
                      command=self._show_donate).pack(side="left", padx=0, pady=8)
        ctk.CTkButton(self.toolbar, text="서포트 서버", image=get_icon("server"), **btn_cfg,
                      fg_color="transparent", hover_color="#2a2a2a",
                      command=self._show_server).pack(side="left", padx=0, pady=8)

        self.title_label = ctk.CTkLabel(
            self.toolbar, text="(Untitled)",
            font=ctk.CTkFont(size=18, weight="bold"), anchor="e"
        )
        self.title_label.pack(side="right", padx=16)

        # 시작 시 저장된 인증 확인
        self.after(500, self._check_saved_auth)

    def _build_sidebar(self):
        ctk.CTkLabel(self.sidebar, text="노드 목록",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(12, 4), padx=8)

        self.node_listbox = ctk.CTkScrollableFrame(self.sidebar, corner_radius=6)
        self.node_listbox.pack(fill="both", expand=True, padx=6, pady=4)

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(fill="x", padx=6, pady=6)

        ctk.CTkButton(bottom, text="노드 추가", image=get_icon("plus"), height=30,
                      command=self._add_node).pack(fill="x", pady=2)
        ctk.CTkButton(bottom, image=get_icon("remove"),text="노드 삭제", height=30,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=self._delete_node).pack(fill="x", pady=2)

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self.content, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=8)

        self.tabview.add("캐릭터 정보")
        self.tabview.add("노드 편집")
        self.tabview.add("노드 흐름")

        self._build_meta_tab()
        self._build_node_tab()
        self._build_flow_tab()

        self.tabview.configure(command=self._on_tab_change)

    def _build_meta_tab(self):
        from ui.pages.meta_page import MetaPage
        self.meta_page = MetaPage(
            self.tabview.tab("캐릭터 정보"),
            on_change=self._on_meta_change,
            get_save_path=lambda: self.project.save_path
        )
        self.meta_page.pack(fill="both", expand=True)

    def _on_meta_change(self, meta):
        self.project.meta = meta
        self.title_label.configure(text=meta.name or "(Untitled)")
        self.after(300, self._run_checks)

    def _build_node_tab(self):
        from ui.pages.node_page import NodePage
        self.node_page = NodePage(
            self.tabview.tab("노드 편집"),
            on_change=self._on_node_change,
            get_emotions=lambda: self.meta_page.get_emotions(),
            get_skins=lambda: self.meta_page.get_skin_names()
        )
        self.node_page.pack(fill="both", expand=True)

    def _run_checks(self):
        if self._is_loading:
            return
        # 현재 편집 중인 노드 저장 후 검사
        self.node_page._save_current(target_node=self.node_page._node)
        from core.validator import check_project, verify_integrity
        errors = check_project(self.project)
        integrity = verify_integrity(self.project, self.project.save_path or "")
        self.status_bar.update_status(errors, integrity)

    def _on_node_change(self, node: Node):
        for i, n in enumerate(self.project.nodes):
            if n.name == node.name:
                self.project.nodes[i] = node
                break
        self.flow_page._project = self.project
        self.after(300, self._run_checks)  # 디바운스

    def _load_node(self, name: str):
        self._selected_node = name
        node = self.project.get_node(name)
        if node:
            def _do():
                self.node_page.load_node(node, self.project.node_names())
                self.tabview.set("노드 편집")
                self._refresh_node_list()
                # 노드 선택 시 flow_page 도 즉시 갱신
                self.flow_page._project = self.project
            self._show_area_loading(_do)
        else:
            self._refresh_node_list()

    def _build_flow_tab(self):
        from ui.pages.flow_page import FlowPage
        self.flow_page = FlowPage(self.tabview.tab("노드 흐름"))
        self.flow_page.pack(fill="both", expand=True)

    # ─────────────────────────────────────────
    # 로딩 오버레이 (두 종류)
    # ─────────────────────────────────────────
    def _show_full_loading(self, callback):
        """전체 화면 로딩 — 새 프로젝트, 불러오기 등 무거운 작업"""
        overlay = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        ctk.CTkLabel(
            overlay, text="로딩 중...",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="gray50"
        ).place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()
        self.after(80, lambda: self._run_and_close(callback, overlay))

    def _show_area_loading(self, callback):
        self.update_idletasks()

        # tabview 기준으로 위치/크기 계산
        tv_x = self.tabview.winfo_x()
        tv_y = self.tabview.winfo_y()
        tv_w = self.tabview.winfo_width()
        tv_h = self.tabview.winfo_height()

        tab_btn_h = 35 # 크기를 줄이면 y가 커짐
        pad = 8

        overlay = ctk.CTkFrame(
            self.content,
            fg_color="#252525",
            corner_radius=16,
            width=tv_w - pad * 2,
            height=tv_h - tab_btn_h - pad * 2
        )
        overlay.place(x=tv_x + pad, y=tv_y + tab_btn_h + pad)
        overlay.lift()
        overlay.pack_propagate(False)

        ctk.CTkLabel(
            overlay, text="로딩 중...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="gray50"
        ).place(relx=0.5, rely=0.5, anchor="center")

        self.update_idletasks()
        self.after(80, lambda: self._run_and_close(callback, overlay))

    def _run_and_close(self, callback, overlay):
        try:
            callback()
        finally:
            self.after(150, overlay.destroy)

    # ─────────────────────────────────────────
    # 노드 목록 조작
    # ─────────────────────────────────────────
    def _refresh_node_list(self):
        for w in self.node_listbox.winfo_children():
            w.destroy()

        for node in self.project.nodes:
            is_special = True if node.name == "_START" else None
            label = get_icon("settings") if is_special else get_icon("node")

            btn = ctk.CTkButton(
                self.node_listbox, text=node.name, image=label, height=32, anchor="w",
                fg_color=("#2b4f6e" if node.name == self._selected_node else "transparent"),
                hover_color="#1e3a52", text_color="white",
                command=lambda n=node.name: self._load_node(n)
            )
            btn.pack(fill="x", pady=1)


    def _add_node(self):
        dialog = ctk.CTkInputDialog(text="새 노드 이름 (한글/영문/숫자/-_):", title="노드 추가")
        name = dialog.get_input()
        if not name:
            return

        from utils.helpers import is_valid_node_name
        if not is_valid_node_name(name):
            messagebox.showerror("오류", "노드 이름에 사용할 수 없는 문자가 포함되어 있습니다.")
            return

        if name in self.project.node_names():
            messagebox.showerror("오류", f"[{name}] 노드가 이미 존재합니다.")
            return

        from core.models import Node, Dialogue, Step
        new_node = Node(
            name=name,
            dialogues=[Dialogue(id=f"{name}_01", steps=[Step()])],
            buttons=[]
        )
        self.project.nodes.append(new_node)

        # _START 항상 최상단 유지
        self.project.nodes.sort(key=lambda n: (0 if n.name == "_START" else 1))

        self._refresh_node_list()
        self._load_node(name)

    def _delete_node(self):
        if not self._selected_node:
            return
        if self._selected_node == "_START":  # ← _END 제거
            messagebox.showwarning("경고", "_START 노드는 삭제할 수 없습니다.")
            return
        if not messagebox.askyesno("삭제 확인", f"[{self._selected_node}] 노드를 삭제할까요?"):
            return

        self.project.nodes = [n for n in self.project.nodes if n.name != self._selected_node]
        self._selected_node = "_START"
        self._refresh_node_list()
        self._load_node("_START")
    # ─────────────────────────────────────────
    # 로그인
    # ─────────────────────────────────────────
    def _check_saved_auth(self):
        from core.auth import get_saved_auth, refresh_plan, save_auth
        auth = get_saved_auth()
        if auth:
            def _refresh():
                plan = refresh_plan(auth["user_id"])
                auth["plan"] = plan
                save_auth(auth)
                self.after(0, lambda: self._update_login_ui(auth))
            import threading
            threading.Thread(target=_refresh, daemon=True).start()
        else:
            self._update_login_ui(None)

        # 1시간마다 재체크
        self.after(3600 * 1000, self._check_saved_auth)

    def _update_login_ui(self, auth: dict | None):
        if auth:
            plan = auth.get("plan", "free")
            plan_color = {
                "컬렉터": "#FFD700",
                "스타터": "#4a9eff",
                "free": "gray70"
            }.get(plan, "gray70")

            self._login_btn.configure(
                text=f"{plan}",
                fg_color="transparent",
                hover_color="#2a2a2a",
                text_color=plan_color,
                command=self._handle_logout
            )
        else:
            self._login_btn.configure(
                text="로그인",
                fg_color="#5865F2",
                hover_color="#4752c4",
                text_color="white",
                command=self._handle_login
            )

    def _handle_login(self):
        from core.auth import login_with_discord

        self._login_btn.configure(
            state="disabled", text="로그인 중..."
        )

        def on_complete(auth):
            self.after(0, lambda: self._update_login_ui(auth))
            self.after(0, lambda: self._login_btn.configure(state="normal"))

        def on_error(msg):
            self.after(0, lambda: self._login_btn.configure(state="normal"))
            self.after(0, lambda: messagebox.showerror("로그인 실패", msg))

        login_with_discord(on_complete=on_complete, on_error=on_error)

    def _handle_logout(self):
        if messagebox.askyesno("로그아웃", "로그아웃 하시겠습니까?"):
            from core.auth import clear_auth
            clear_auth()
            self._update_login_ui(None)
    # ─────────────────────────────────────────
    # 파일 조작
    # ─────────────────────────────────────────
    def _new_project(self):
        if messagebox.askyesno("새 프로젝트", "현재 작업을 버리고 새 프로젝트를 만들까요?"):
            def _do():
                self._is_loading = True
                self.project = new_project()
                self.project.save_path = None
                self._selected_node = "_START"
                self.meta_page.load_meta(self.project.meta, is_saved=False)
                self._refresh_node_list()
                self.node_page.load_node(
                    self.project.get_node("_START"),
                    self.project.node_names()
                )
                self.tabview.set("노드 편집")
                self.title_label.configure(text="(Untitled)")
                def _finish():
                    self._is_loading = False
                    self._run_checks()
                self.after(800, _finish)
            self._show_full_loading(_do)

    def _open_project(self):
        folder = filedialog.askdirectory(title="캐릭터 폴더 선택")
        if not folder:
            return
        try:
            project = load_project(folder)
        except Exception as e:
            messagebox.showerror("열기 실패", str(e))
            return

        def _do():
            self._is_loading = True
            self.project = project
            self._selected_node = "_START"
            self.meta_page.load_meta(self.project.meta, is_saved=True)
            self._refresh_node_list()
            self.node_page.load_node(
                self.project.get_node("_START"),
                self.project.node_names()
            )
            self.tabview.set("노드 편집")
            self.title_label.configure(text=self.project.meta.name or "캐릭터")
            # 불러오기 완료 후 검사 실행 (딜레이 줘서 완전히 로드된 후)
            def _finish():
                self._is_loading = False
                self._run_checks()
            self.after(800, _finish)

        self._show_full_loading(_do)

    def _save_project(self):
        if not self.project.save_path:
            self._save_as_project()
            return
        self._do_save(self.project.save_path)

    def _save_as_project(self):
        folder = filedialog.askdirectory(title="저장할 폴더 선택")
        if not folder:
            return
        char_name = self.project.meta.name or "캐릭터"
        save_path = str(Path(folder) / char_name)
        self._do_save(save_path)

    def _do_save(self, path: str):
        if not self.project.meta.name.strip():
            messagebox.showerror("저장 실패", "캐릭터 이름을 입력해주세요.")
            self.tabview.set("캐릭터 정보")
            return

        # 적법성 검사 통과 여부 확인
        if self.status_bar.has_errors():
            messagebox.showerror(
                "저장 불가",
                "적법성 검사를 통과하지 못했습니다.\n"
                "상태바에 마우스를 올려 오류를 확인하세요."
            )
            return

        warnings = validate_project(self.project)
        if warnings:
            msg = "다음 경고가 있습니다. 그래도 저장할까요?\n\n" + "\n".join(f"• {w}" for w in warnings)
            if not messagebox.askyesno("저장 경고", msg):
                return
        try:
            save_project(self.project, path)
            self.flow_page.save_layout()
            self.meta_page.load_meta(self.project.meta, is_saved=True)
            from core.config import set_last_path
            set_last_path(path)
            self.after(100, self._run_checks)  # ← 추가
            messagebox.showinfo("저장 완료", f"저장되었습니다.\n{path}")
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))
    def _show_credits(self):
        import sys
        import re
        import webbrowser
        import tkinter as tk
        from pathlib import Path

        def _parse_inline(text_widget, line: str, add_link_fn):
            pattern = re.compile(r"(\*\*.*?\*\*|\[.*?\]\(.*?\))")
            parts = pattern.split(line)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    text_widget.insert("end", part[2:-2], "bold")
                elif re.match(r"\[.*?\]\(.*?\)", part):
                    m = re.match(r"\[(.*?)\]\((.*?)\)", part)
                    if m:
                        label, url = m.group(1), m.group(2)
                        tag = add_link_fn(url)
                        text_widget.insert("end", label, tag)
                    else:
                        text_widget.insert("end", part, "normal")
                else:
                    text_widget.insert("end", part, "normal")

        if getattr(sys, 'frozen', False):
            credits_path = Path(sys.executable).parent / "CREDITS.md"
        else:
            credits_path = Path(__file__).parent.parent / "CREDITS.md"

        if not credits_path.exists():
            messagebox.showinfo("크레딧", "CREDITS.md 파일이 없습니다.")
            return

        with open(credits_path, encoding="utf-8") as f:
            content = f.read()

        dialog = ctk.CTkToplevel(self)
        dialog.title("크레딧")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        text = tk.Text(dialog, wrap="word", bg="#1a1a1a", fg="white",
                       font=("맑은 고딕", 11), relief="flat",
                       padx=16, pady=12, cursor="arrow",
                       selectbackground="#2b4f6e")
        text.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        text.tag_configure("h1", font=("맑은 고딕", 16, "bold"), foreground="#4a9eff", spacing3=6)
        text.tag_configure("h2", font=("맑은 고딕", 13, "bold"), foreground="#7ec8e3", spacing3=4)
        text.tag_configure("h3", font=("맑은 고딕", 11, "bold"), foreground="#aed6f1", spacing3=2)
        text.tag_configure("bold", font=("맑은 고딕", 11, "bold"))
        text.tag_configure("bullet", lmargin1=16, lmargin2=28, foreground="#cccccc")
        text.tag_configure("normal", foreground="#dddddd")

        _link_tags = {}

        def _add_link(url: str) -> str:
            tag = f"link_{len(_link_tags)}"
            _link_tags[tag] = url
            text.tag_configure(tag, foreground="#4a9eff", underline=True)
            text.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
            text.tag_bind(tag, "<Enter>", lambda e: text.configure(cursor="hand2"))
            text.tag_bind(tag, "<Leave>", lambda e: text.configure(cursor="arrow"))
            return tag

        for line in content.splitlines():
            if line.startswith("# "):
                text.insert("end", line[2:] + "\n", "h1")
            elif line.startswith("## "):
                text.insert("end", line[3:] + "\n", "h2")
            elif line.startswith("### "):
                text.insert("end", line[4:] + "\n", "h3")
            elif line.startswith("- "):
                text.insert("end", "  • ", "bullet")
                _parse_inline(text, line[2:], _add_link)
                text.insert("end", "\n", "bullet")
            elif line.strip() == "":
                text.insert("end", "\n")
            else:
                _parse_inline(text, line, _add_link)
                text.insert("end", "\n")

        text.configure(state="disabled")

        ctk.CTkButton(dialog, text="닫기", width=100,
                      command=dialog.destroy).pack(pady=8)
    def _show_donate(self):
        import sys
        from pathlib import Path

        if getattr(sys, 'frozen', False):
            qr_path = Path(sys.executable).parent / "assets" / "donateqr.png"
        else:
            qr_path = Path(__file__).parent.parent / "assets" / "donateqr.png"

        dialog = ctk.CTkToplevel(self)
        dialog.title("후원하기")
        dialog.geometry("360x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="후원하기",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dialog, text="개발 지속에 큰 힘이 됩니다",
                     text_color="gray70").pack(pady=(0, 16))

        if qr_path.exists():
            try:
                from PIL import Image
                img = Image.open(qr_path).convert("RGBA")
                img.thumbnail((280, 280))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=(img.width, img.height))
                ctk.CTkLabel(dialog, image=ctk_img, text="").pack(pady=8)
            except Exception:
                ctk.CTkLabel(dialog, text="QR 이미지를 불러올 수 없습니다.",
                             text_color="gray").pack(pady=8)
        else:
            ctk.CTkLabel(dialog, text="QR 이미지가 없습니다.",
                         text_color="gray").pack(pady=8)

        ctk.CTkButton(dialog, text="닫기", width=100,
                      command=dialog.destroy).pack(pady=16)
    def _show_server(self):
        import sys
        import webbrowser
        from pathlib import Path

        if getattr(sys, 'frozen', False):
            qr_path = Path(sys.executable).parent / "assets" / "serverqr.png"
        else:
            qr_path = Path(__file__).parent.parent / "assets" / "serverqr.png"

        dialog = ctk.CTkToplevel(self)
        dialog.title("서포트 서버")
        dialog.geometry("360x480")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="서포트 서버",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dialog,
                     text="커뮤니티에 합류하여 멋진 경험을 해보세요!",
                     text_color="gray70").pack(pady=(0, 12))

        if qr_path.exists():
            try:
                from PIL import Image
                img = Image.open(qr_path).convert("RGBA")
                img.thumbnail((260, 260))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=(img.width, img.height))
                ctk.CTkLabel(dialog, image=ctk_img, text="").pack(pady=8)
            except Exception:
                ctk.CTkLabel(dialog, text="QR 이미지를 불러올 수 없습니다.",
                             text_color="gray").pack(pady=8)
        else:
            ctk.CTkLabel(dialog, text="QR 이미지가 없습니다.",
                         text_color="gray").pack(pady=8)

        # 하이퍼링크
        link_btn = ctk.CTkButton(
            dialog, text="discord.gg/panette",
            fg_color="transparent", hover_color="#2a2a2a",
            text_color="#4a9eff",
            font=ctk.CTkFont(size=13, underline=True),
            command=lambda: webbrowser.open("https://discord.gg/panette")
        )
        link_btn.pack(pady=4)

        ctk.CTkButton(dialog, text="닫기", width=100,
                      command=dialog.destroy).pack(pady=(8, 16))
    # ─────────────────────────────────────────
    # 탭 전환
    # ─────────────────────────────────────────
    def _on_tab_change(self):
        current = self.tabview.get()

        def _do():
            if current == "노드 흐름":
                self.flow_page.render(self.project)
            elif current == "노드 편집":
                if self._selected_node:
                    self.node_page.load_node(
                        self.project.get_node(self._selected_node),
                        self.project.node_names()
                    )
            elif current == "캐릭터 정보":
                self.meta_page._refresh_emotion_list()

        self._show_area_loading(_do)
