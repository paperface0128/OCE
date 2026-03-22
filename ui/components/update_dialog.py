import customtkinter as ctk
import threading


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, update_info: dict):
        super().__init__(parent)
        self.title("업데이트 가능")
        self.resizable(False, False)
        self.grab_set()
        self._info = update_info
        self._force = update_info.get("force", False)
        self._build()

        # notes 수에 따라 높이 동적 조정
        notes_count = min(len(self._info.get("notes", [])), 6)
        base_height = 280
        notes_height = notes_count * 24
        force_height = 40 if self._force else 0
        height = base_height + notes_height + force_height
        self.geometry(f"440x{height}")
        self.minsize(440, height)

        if self._force:
            self.protocol("WM_DELETE_WINDOW", lambda: None)

    def _build(self):
        if self._force:
            ctk.CTkLabel(self, text="필수 업데이트",
                         font=ctk.CTkFont(size=16, weight="bold"),
                         text_color="#ff5252").pack(pady=(20, 4))
        else:
            ctk.CTkLabel(self, text="새 버전이 있습니다!",
                         font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 4))

        ctk.CTkLabel(self, text=f"v{self._info['version']}",
                     font=ctk.CTkFont(size=13),
                     text_color="#4a9eff").pack(pady=(0, 12))

        if self._force:
            ctk.CTkLabel(self,
                         text="이 업데이트는 필수입니다.\n업데이트 후 계속 사용할 수 있습니다.",
                         text_color="#ffab40",
                         font=ctk.CTkFont(size=11)).pack(pady=(0, 8))

        if self._info.get("notes"):
            note_frame = ctk.CTkFrame(self, corner_radius=8)
            note_frame.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(note_frame, text="변경사항",
                         font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
            for note in self._info["notes"][:6]:
                ctk.CTkLabel(note_frame, text=f"  • {note}",
                             font=ctk.CTkFont(size=11),
                             text_color="gray70",
                             anchor="w").pack(fill="x", padx=12)
            ctk.CTkFrame(note_frame, height=8, fg_color="transparent").pack()

        self._progress = ctk.CTkProgressBar(self, width=360)
        self._progress.pack(pady=(16, 4))
        self._progress.set(0)
        self._progress_label = ctk.CTkLabel(self, text="", text_color="gray60",
                                             font=ctk.CTkFont(size=11))
        self._progress_label.pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=16)

        self._update_btn = ctk.CTkButton(
            btn_row, text="지금 업데이트", width=140,
            command=self._start_update
        )
        self._update_btn.pack(side="left", padx=8)

        # 강제 업데이트면 나중에 버튼 숨김
        if not self._force:
            ctk.CTkButton(
                btn_row, text="나중에", width=80,
                fg_color="transparent", hover_color="#2a2a2a",
                command=self.destroy
            ).pack(side="left", padx=8)

    def _start_update(self):
        self._update_btn.configure(state="disabled", text="업데이트 중...")

        def run():
            from core.updater import download_and_apply

            def on_progress(percent):
                self._progress.set(percent / 100)
                self._progress_label.configure(text=f"{percent}%")

            success = download_and_apply(
                self._info["url"],
                self._info["version"],
                progress_callback=on_progress
            )

            if success:
                self._progress.set(1.0)
                self._progress_label.configure(
                    text="완료! 3초 후 자동 재시작됩니다.",
                    text_color="#00e676"
                )
                self._update_btn.configure(text="✅ 완료", state="disabled")
                # 3초 후 자동 재시작
                self.winfo_toplevel().after(3000, self._restart)
            else:
                self._progress_label.configure(
                    text="업데이트 실패. 다시 시도해주세요.",
                    text_color="#ff5252"
                )
                self._update_btn.configure(state="normal", text="⬇ 다시 시도")

        threading.Thread(target=run, daemon=True).start()
    def _restart(self):
        import os
        # OCE_updater.exe가 재실행 담당 (updater_helper.py)
        self.winfo_toplevel().after(1000, lambda: os._exit(0))