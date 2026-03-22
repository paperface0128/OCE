import customtkinter as ctk
import tkinter as tk
from core.hangul import filter_and_sort


class ScrollableDropdown:
    def __init__(self, anchor_widget, values: list[str], variable: ctk.StringVar,
                 on_select=None, max_visible: int = 8):
        self._anchor = anchor_widget
        self._all_values = values
        self._var = variable
        self._on_select = on_select
        self._max_visible = max_visible
        self._popup = None
        self._root_bind_id = None
        self._canvas = None
        self._inner = None
        self._scroll_handler = None
        self._after_id = None  # 디바운스용

    def toggle(self):
        if self._popup:
            try:
                if self._popup.winfo_exists():
                    self._close()
                    return
            except Exception:
                self._popup = None
        self._open()

    def _open(self):
        root = self._anchor.winfo_toplevel()

        # ── 검색 Entry를 앵커 위에 겹쳐서 배치 (IME 문제 해결) ──
        ax = self._anchor.winfo_rootx() - root.winfo_rootx()
        ay = self._anchor.winfo_rooty() - root.winfo_rooty()
        aw = self._anchor.winfo_width()
        ah = self._anchor.winfo_height()

        self._search_var = tk.StringVar()
        self._search_frame = tk.Frame(root, bg="#252540",
                                       highlightbackground="#4a9eff",
                                       highlightthickness=1)
        self._search_entry = tk.Entry(
            self._search_frame, textvariable=self._search_var,
            bg="#252540", fg="white", insertbackground="white",
            font=("Arial", 11), relief="flat", bd=6,
            highlightthickness=0
        )
        self._search_entry.pack(fill="both", expand=True)
        self._search_frame.place(x=ax, y=ay, width=aw, height=ah)
        self._search_frame.lift()
        self._search_entry.focus_set()

        # ── 팝업 (리스트만) ──
        self._popup = tk.Toplevel(root)
        self._popup.wm_overrideredirect(True)
        self._popup.withdraw()

        w = max(aw, 240)
        item_h = 28
        visible = min(self._max_visible, len(self._all_values))
        list_h = visible * item_h

        outer = tk.Frame(self._popup, bg="#1a1a2e",
                         highlightbackground="#4a9eff", highlightthickness=1)
        outer.pack(fill="both", expand=True)

        list_frame = tk.Frame(outer, bg="#1a1a2e")
        list_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(list_frame, bg="#1a1a2e",
                                  highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg="#1a1a2e")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw"
        )

        def on_frame_configure(e):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        def on_canvas_configure(e):
            self._canvas.itemconfig(self._canvas_window, width=e.width)

        self._inner.bind("<Configure>", on_frame_configure)
        self._canvas.bind("<Configure>", on_canvas_configure)

        def on_scroll(e):
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            return "break"

        self._scroll_handler = on_scroll
        self._canvas.bind("<MouseWheel>", on_scroll)
        self._inner.bind("<MouseWheel>", on_scroll)

        self._render_list(self._all_values)

        # 검색
        def on_search_change(*_):
            if self._after_id:
                try:
                    self._popup.after_cancel(self._after_id)
                except Exception:
                    pass
            self._after_id = self._popup.after(
                60, lambda: self._do_search(self._search_var.get())
            )

        self._search_var.trace_add("write", on_search_change)
        self._search_entry.bind("<KeyRelease>", lambda e: on_search_change())

        # 팝업 위치 (검색창 바로 아래)
        popup_y = self._anchor.winfo_rooty() + ah
        screen_h = self._popup.winfo_screenheight()
        if popup_y + list_h > screen_h:
            popup_y = self._anchor.winfo_rooty() - list_h

        self._popup.update_idletasks()
        self._popup.geometry(f"{w}x{list_h}+{self._anchor.winfo_rootx()}+{popup_y}")
        self._popup.deiconify()

        self._root_bind_id = root.bind("<Button-1>", self._on_root_click, add="+")

    def _do_search(self, query: str):
        if not self._canvas:
            return
        filtered = filter_and_sort(query.strip(), self._all_values)
        self._render_list(filtered)

    def _render_list(self, values: list[str]):
        if not self._inner:
            return

        for w in self._inner.winfo_children():
            w.destroy()

        current = self._var.get()
        for val in values:
            is_selected = val == current
            bg = "#1e3a52" if is_selected else "#1a1a2e"

            item_frame = tk.Frame(self._inner, bg=bg, height=28, cursor="hand2")
            item_frame.pack(fill="x")
            item_frame.pack_propagate(False)

            label = tk.Label(item_frame, text=val, bg=bg,
                             fg="white", font=("Arial", 11),
                             anchor="w", padx=8, cursor="hand2")
            label.pack(fill="both", expand=True)

            def on_enter(e, f=item_frame, l=label):
                f.configure(bg="#2b4f6e")
                l.configure(bg="#2b4f6e")

            def on_leave(e, f=item_frame, l=label, b=bg):
                f.configure(bg=b)
                l.configure(bg=b)

            def on_click(e, v=val):
                self._var.set(v)
                if self._on_select:
                    self._on_select(v)
                self._close()

            for w_ in [item_frame, label]:
                w_.bind("<Enter>", on_enter)
                w_.bind("<Leave>", on_leave)
                w_.bind("<Button-1>", on_click)
                if self._scroll_handler:
                    w_.bind("<MouseWheel>", self._scroll_handler)

        if self._canvas:
            self._canvas.yview_moveto(0)

    def _on_focus_out(self, event):
        """메인 창이 포커스를 잃으면 닫기"""
        try:
            if self._popup and self._popup.winfo_exists():
                # 포커스가 팝업으로 이동한 경우는 닫지 않음
                focused = self._popup.focus_get()
                if focused is None:
                    self._close()
        except Exception:
            pass

    def _on_root_click(self, event):
        if not self._popup:
            return
        try:
            if not self._popup.winfo_exists():
                self._close()
                return
            px = self._popup.winfo_rootx()
            py = self._popup.winfo_rooty()
            pw = self._popup.winfo_width()
            ph = self._popup.winfo_height()
            bx = self._anchor.winfo_rootx()
            by = self._anchor.winfo_rooty()
            bw = self._anchor.winfo_width()
            bh = self._anchor.winfo_height()

            in_popup = (px <= event.x_root <= px + pw and
                        py <= event.y_root <= py + ph)
            in_btn = (bx <= event.x_root <= bx + bw and
                      by <= event.y_root <= by + bh)

            if not in_popup and not in_btn:
                self._close()
        except Exception:
            self._close()

    def _close(self):
        # 검색 프레임 제거
        if hasattr(self, '_search_frame') and self._search_frame:
            try:
                self._search_frame.destroy()
            except Exception:
                pass
            self._search_frame = None
            self._search_entry = None

        try:
            root = self._anchor.winfo_toplevel()
            if self._root_bind_id:
                root.unbind("<Button-1>", self._root_bind_id)
            root.unbind("<FocusOut>")
        except Exception:
            pass

        self._root_bind_id = None
        self._canvas = None
        self._inner = None
        self._scroll_handler = None

        if self._after_id:
            try:
                if self._popup and self._popup.winfo_exists():
                    self._popup.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None