import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=24, corner_radius=0, **kwargs)
        self._errors: list[str] = []
        self._integrity: list[str] = []
        self._tooltip_frame: ctk.CTkFrame | None = None
        self._tooltip_after: str | None = None
        self._integrity_tooltip_frame: ctk.CTkFrame | None = None
        self._integrity_tooltip_after: str | None = None
        self._build()

    def _build(self):
        self.pack_propagate(False)

        from utils.icons import get_icon

        # 적법성 아이콘 + 라벨
        indicator_frame = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        indicator_frame.pack(side="left", padx=12)

        self._indicator_icon = ctk.CTkLabel(
            indicator_frame, text="",
            image=get_icon("info", 14),
            cursor="hand2"
        )
        self._indicator_icon.pack(side="left", padx=(0, 4))

        self._indicator = ctk.CTkLabel(
            indicator_frame, text="검사 중...",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            cursor="hand2"
        )
        self._indicator.pack(side="left")

        indicator_frame.bind("<Enter>", self._show_tooltip)
        self._indicator_icon.bind("<Enter>", self._show_tooltip)
        self._indicator.bind("<Enter>", self._show_tooltip)
        self._indicator_frame = indicator_frame

        # 미저장 아이콘 + 라벨
        integrity_frame = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        integrity_frame.pack(side="right", padx=12)

        self._integrity_icon = ctk.CTkLabel(
            integrity_frame, text="",
            cursor="hand2"
        )
        self._integrity_icon.pack(side="left", padx=(0, 4))

        self._integrity_label = ctk.CTkLabel(
            integrity_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            cursor="hand2"
        )
        self._integrity_label.pack(side="left")

        integrity_frame.bind("<Enter>", self._show_integrity_tooltip)
        self._integrity_icon.bind("<Enter>", self._show_integrity_tooltip)
        self._integrity_label.bind("<Enter>", self._show_integrity_tooltip)
        self._integrity_frame = integrity_frame

    def update_status(self, errors: list[str], integrity: list[str]):
        self._errors = errors
        self._integrity = integrity

        from utils.icons import get_icon

        if not errors:
            self._indicator_icon.configure(image=get_icon("ok", 14))
            self._indicator.configure(text="적법성 검사 통과", text_color="#00e676")
            self.configure(fg_color="#0d2b1a")
        else:
            self._indicator_icon.configure(image=get_icon("cross", 14))
            self._indicator.configure(text=f"{len(errors)}개 오류", text_color="#ff5252")
            self.configure(fg_color="#2b0d0d")

        if integrity:
            self._integrity_icon.configure(image=get_icon("warn", 14))
            self._integrity_label.configure(
                text=f"미저장 변경 {len(integrity)}건",
                text_color="#ffab40"
            )
        else:
            from PIL import Image
            blank = ctk.CTkImage(Image.new("RGBA", (14, 14), (0,0,0,0)), size=(14, 14))
            self._integrity_icon.configure(image=blank)
            self._integrity_label.configure(text="")

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    # ─────────────────────────────────────────
    # 공통 유틸
    # ─────────────────────────────────────────
    def _is_over(self, widget) -> bool:
        try:
            mx = self.winfo_pointerx()
            my = self.winfo_pointery()

            targets = [widget]
            if hasattr(self, '_indicator_frame'):
                targets.append(self._indicator_frame)

            for w in targets:
                rx = w.winfo_rootx()
                ry = w.winfo_rooty()
                if rx <= mx <= rx + w.winfo_width() and ry <= my <= ry + w.winfo_height():
                    return True
            return False
        except Exception:
            return False

    def _make_tooltip_frame(self, anchor_widget, text: str, align: str = "left") -> ctk.CTkFrame:
        root = self.winfo_toplevel()
        frame = ctk.CTkFrame(
            root, corner_radius=8,
            fg_color="#1e1e2e",
            border_width=1, border_color="#555"
        )
        ctk.CTkLabel(
            frame, text=text,
            font=ctk.CTkFont(size=11),
            justify="left"
        ).pack(padx=12, pady=8)

        frame.update_idletasks()
        ax = anchor_widget.winfo_rootx() - root.winfo_rootx()
        ay = anchor_widget.winfo_rooty() - root.winfo_rooty() + 26

        if align == "right":
            fw = frame.winfo_reqwidth()
            ax = ax + anchor_widget.winfo_width() - fw

        frame.place(x=ax, y=ay)
        frame.lift()
        return frame

    # ─────────────────────────────────────────
    # 적법성 툴팁
    # ─────────────────────────────────────────
    def _show_tooltip(self, event=None):
        if self._tooltip_frame is not None:
            return

        if not self._errors:
            text = "✅ 완벽합니다!\n모든 검사를 통과했습니다."
        else:
            lines = ["❌ 적법성 오류:"]
            for e in self._errors:
                lines.append(f"  • {e}")
            text = "\n".join(lines)

        self._tooltip_frame = self._make_tooltip_frame(self._indicator, text, align="left")
        self._tooltip_after = self.after(100, self._poll_tooltip)

    def _poll_tooltip(self):
        if not self._tooltip_frame:
            return
        if not self._is_over(self._indicator) and not self._is_over(self._tooltip_frame):
            self._destroy_tooltip()
        else:
            self._tooltip_after = self.after(100, self._poll_tooltip)

    def _destroy_tooltip(self):
        if self._tooltip_after:
            try:
                self.after_cancel(self._tooltip_after)
            except Exception:
                pass
            self._tooltip_after = None
        if self._tooltip_frame:
            try:
                self._tooltip_frame.destroy()
            except Exception:
                pass
            self._tooltip_frame = None

    # ─────────────────────────────────────────
    # 미저장 툴팁
    # ─────────────────────────────────────────
    def _show_integrity_tooltip(self, event=None):
        if not self._integrity:
            return
        if self._integrity_tooltip_frame is not None:
            return

        lines = ["⚠ 미저장 변경사항:"]
        for n in self._integrity:
            lines.append(f"  • {n}")
        text = "\n".join(lines)

        self._integrity_tooltip_frame = self._make_tooltip_frame(
            self._integrity_label, text, align="right"
        )
        self._integrity_tooltip_after = self.after(100, self._poll_integrity_tooltip)

    def _poll_integrity_tooltip(self):
        if not self._integrity_tooltip_frame:
            return
        if not self._is_over(self._integrity_label) and not self._is_over(self._integrity_tooltip_frame):
            self._destroy_integrity_tooltip()
        else:
            self._integrity_tooltip_after = self.after(100, self._poll_integrity_tooltip)

    def _destroy_integrity_tooltip(self):
        if self._integrity_tooltip_after:
            try:
                self.after_cancel(self._integrity_tooltip_after)
            except Exception:
                pass
            self._integrity_tooltip_after = None
        if self._integrity_tooltip_frame:
            try:
                self._integrity_tooltip_frame.destroy()
            except Exception:
                pass
            self._integrity_tooltip_frame = None