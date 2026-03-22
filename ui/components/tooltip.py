import customtkinter as ctk


class Tooltip:
    """info 아이콘에 마우스 올리면 툴팁 표시"""

    def __init__(self, parent, text: str):
        from utils.icons import get_icon
        self._text = text
        self._tooltip_frame = None
        self._after_id = None

        self._label = ctk.CTkLabel(
            parent, text="",
            image=get_icon("info", 16),
            width=20, height=20,
            cursor="hand2"
        )

        self._label.bind("<Enter>", self._show)
        self._label.bind("<Leave>", self._hide)

    def pack(self, **kwargs):
        self._label.pack(**kwargs)

    def grid(self, **kwargs):
        self._label.grid(**kwargs)

    def _show(self, event=None):
        if self._tooltip_frame:
            return

        root = self._label.winfo_toplevel()
        self._tooltip_frame = ctk.CTkFrame(
            root, corner_radius=8,
            fg_color="#1e1e2e",
            border_width=1, border_color="#555"
        )

        ctk.CTkLabel(
            self._tooltip_frame,
            text=self._text,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=300
        ).pack(padx=12, pady=8)

        self._tooltip_frame.update_idletasks()

        # 위치 계산
        lx = self._label.winfo_rootx() - root.winfo_rootx()
        ly = self._label.winfo_rooty() - root.winfo_rooty()
        fw = self._tooltip_frame.winfo_reqwidth()
        fh = self._tooltip_frame.winfo_reqheight()

        # 오른쪽에 띄우되 화면 벗어나면 왼쪽으로
        tx = lx + 24
        ty = ly - fh // 2

        # 화면 경계 체크
        root_w = root.winfo_width()
        if tx + fw > root_w:
            tx = lx - fw - 4

        self._tooltip_frame.place(x=tx, y=ty)
        self._tooltip_frame.lift()

        self._after_id = self._label.after(100, self._poll)

    def _poll(self):
        if not self._tooltip_frame:
            return
        try:
            mx = self._label.winfo_pointerx()
            my = self._label.winfo_pointery()
            rx = self._label.winfo_rootx()
            ry = self._label.winfo_rooty()
            rw = self._label.winfo_width()
            rh = self._label.winfo_height()

            over_label = rx <= mx <= rx + rw and ry <= my <= ry + rh

            if self._tooltip_frame:
                fx = self._tooltip_frame.winfo_rootx()
                fy = self._tooltip_frame.winfo_rooty()
                fw = self._tooltip_frame.winfo_width()
                fh = self._tooltip_frame.winfo_height()
                over_tip = fx <= mx <= fx + fw and fy <= my <= fy + fh
            else:
                over_tip = False

            if not over_label and not over_tip:
                self._hide()
            else:
                self._after_id = self._label.after(100, self._poll)
        except Exception:
            self._hide()

    def _hide(self, event=None):
        if self._after_id:
            try:
                self._label.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._tooltip_frame:
            try:
                self._tooltip_frame.destroy()
            except Exception:
                pass
            self._tooltip_frame = None