import customtkinter as ctk
from typing import Callable
from utils.icons import get_icon, btn

OPERATORS = [">=", ">", "<=", "<", "==", "!="]
STATS = ["HP", "STR", "DEP", "INT", "WIS", "SPD"]


class ConditionEditor(ctk.CTkFrame):
    def __init__(self, parent, conditions: dict = None, on_change: Callable = None, **kwargs):
        super().__init__(parent, corner_radius=6, **kwargs)
        self.on_change = on_change
        self._flag_rows: list = []
        self._equipped_rows: list = []
        self._expanded = False
        self._build()
        self.load(conditions or {})

    def _build(self):
        # ── 헤더 (항상 표시) ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(header, text="조건",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        # 툴팁 추가
        from ui.components.tooltip import Tooltip
        Tooltip(header,
            "이 대사가 출력되기 위한 조건입니다.\n"
            "호감도, 시간, 스탯, 플래그, 착용 장비 조건을\n"
            "모두 만족해야 이 대사가 선택됩니다."
        ).pack(side="left", padx=4)

        self._toggle_btn = ctk.CTkButton(
            header, text="펼치기",
            image=get_icon("right", 14),
            compound="left",
            width=90, height=24,
            fg_color="transparent", hover_color="#2a2a2a",
            command=self._toggle,
            anchor="right"
        )
        self._toggle_btn.pack(side="right", padx=4)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._build_content()

    def _build_content(self):
        # ── 호감도 ──
        aff_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        aff_frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(aff_frame, text="호감도", width=70, anchor="w").pack(side="left", padx=(0, 4))
        self._aff_op = ctk.StringVar(value=">=")
        ctk.CTkOptionMenu(aff_frame, variable=self._aff_op, values=OPERATORS,
                          width=65, command=lambda _: self._emit()).pack(side="left", padx=2)
        self._aff_val = ctk.StringVar(value="0")
        ctk.CTkEntry(aff_frame, textvariable=self._aff_val, width=70).pack(side="left", padx=2)
        self._aff_val.trace_add("write", lambda *_: self._emit())

        # ── 시간 ──
        time_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        time_frame.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(time_frame, text="시간", width=70, anchor="w").pack(side="left", padx=(0, 4))
        self._time_start = ctk.StringVar(value="00:00")
        self._time_end = ctk.StringVar(value="23:59")
        ctk.CTkEntry(time_frame, textvariable=self._time_start, width=65).pack(side="left", padx=2)
        ctk.CTkLabel(time_frame, text="~").pack(side="left", padx=2)
        ctk.CTkEntry(time_frame, textvariable=self._time_end, width=65).pack(side="left", padx=2)
        self._time_start.trace_add("write", lambda *_: self._emit())
        self._time_end.trace_add("write", lambda *_: self._emit())

        # ── 스탯 ──
        ctk.CTkLabel(self._content, text="스탯",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(8, 2))  # padx=4 → 12

        stat_grid = ctk.CTkFrame(self._content, fg_color="transparent")
        stat_grid.pack(fill="x", padx=20, pady=2)

        self._stat_ops: dict[str, ctk.StringVar] = {}
        self._stat_vals: dict[str, ctk.StringVar] = {}

        for i, stat in enumerate(STATS):
            row = i // 2
            col = i % 2
            cell = ctk.CTkFrame(stat_grid, fg_color="transparent")
            cell.grid(row=row, column=col, padx=4, pady=2, sticky="w")
            ctk.CTkLabel(cell, text=stat, width=40, anchor="e").pack(side="left", padx=(0, 2))
            op_var = ctk.StringVar(value=">=")
            ctk.CTkOptionMenu(cell, variable=op_var, values=OPERATORS,
                              width=65, command=lambda _: self._emit()).pack(side="left", padx=2)
            val_var = ctk.StringVar(value="0")
            ctk.CTkEntry(cell, textvariable=val_var, width=60).pack(side="left", padx=2)
            val_var.trace_add("write", lambda *_: self._emit())
            self._stat_ops[stat] = op_var
            self._stat_vals[stat] = val_var

        # ── 플래그 ──
        flag_header = ctk.CTkFrame(self._content, fg_color="transparent")
        flag_header.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(flag_header, text="플래그",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(flag_header, text="추가", image=get_icon("plus"), width=70, height=24,
                      command=self._add_flag).pack(side="right")

        self._flag_container = ctk.CTkFrame(self._content, fg_color="transparent", height=0)
        self._flag_container.pack(fill="x", padx=20)
        self._flag_container.pack_propagate(False)  # 비어있을때 공간 안 차지

        # ── 착용 장비 ──
        equip_header = ctk.CTkFrame(self._content, fg_color="transparent")
        equip_header.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(equip_header, text="착용 장비",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(equip_header, text="추가", image=get_icon("plus"), width=70, height=24,
                      command=self._add_equipped).pack(side="right")

        self._equipped_container = ctk.CTkFrame(self._content, fg_color="transparent", height=0)
        self._equipped_container.pack(fill="x", padx=20, pady=(0, 8))
        self._equipped_container.pack_propagate(False)  # 비어있을때 공간 안 차지

    def _toggle(self):
        from utils.icons import get_icon
        self._expanded = not self._expanded
        if self._expanded:
            self._content.pack(fill="x", padx=4, pady=(0, 8))
            self._toggle_btn.configure(
                image=get_icon("down", 14),
                text="접기"
            )
        else:
            self._content.pack_forget()
            self._toggle_btn.configure(
                image=get_icon("right", 14),
                text="펼치기"
            )

    # ─────────────────────────────────────────
    # 플래그 행
    # ─────────────────────────────────────────
    def _update_container_height(self, container:ctk.CTkFrame, rows):
        if rows:
            container.configure(height=len(rows) * 34)
            container.pack_propagate(True)
        else:
            container.configure(height=0)
            container.pack_propagate(False)

    def _add_flag(self, key: str = "", op: str = ">=", val: str = "0"):
        row = ctk.CTkFrame(self._flag_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        key_var = ctk.StringVar(value=key)
        op_var = ctk.StringVar(value=op)
        val_var = ctk.StringVar(value=val)

        ctk.CTkEntry(row, textvariable=key_var, width=120,
                     placeholder_text="플래그 이름").pack(side="left", padx=2)
        ctk.CTkOptionMenu(row, variable=op_var, values=OPERATORS,
                          width=65, command=lambda _: self._emit()).pack(side="left", padx=2)
        ctk.CTkEntry(row, textvariable=val_var, width=60).pack(side="left", padx=2)

        def delete():
            row.destroy()
            self._flag_rows = [(r, k, o, v) for r, k, o, v in self._flag_rows if r != row]
            self._update_container_height(self._flag_container, self._flag_rows)
            self._emit()

        ctk.CTkButton(row, text="", image=get_icon("remove"), width=28, height=24,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=delete).pack(side="left", padx=4)

        key_var.trace_add("write", lambda *_: self._emit())
        val_var.trace_add("write", lambda *_: self._emit())
        self._flag_rows.append((row, key_var, op_var, val_var))
        self._update_container_height(self._flag_container, self._flag_rows)

    def _get_used_equipped_ids(self) -> set:
        used = set()
        for _, val_var in self._equipped_rows:
            try:
                used.add(int(val_var.get().strip()))
            except Exception:
                pass
        return used

    def _add_equipped(self, val: str = ""):
        from core.db_reader import get_all_gears
        from core.icon_cache import get_gear_icon
        from ui.components.scrollable_dropdown import ScrollableDropdown

        gears = get_all_gears()
        if not gears:
            self._add_equipped_text(val)
            return

        used_ids = self._get_used_equipped_ids()
        if val:
            try:
                used_ids.discard(int(val))
            except Exception:
                pass

        available = [g for g in gears if g["id"] not in used_ids]
        if not available:
            return

        row = ctk.CTkFrame(self._equipped_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        all_options = [f"{g['id']}. {g['name']}" for g in gears]
        avail_options = [f"{g['id']}. {g['name']}" for g in available]

        default_id = int(val) if val else available[0]["id"]
        default_option = next(
            (o for o in all_options if o.startswith(f"{default_id}.")), avail_options[0]
        )

        icon_label = ctk.CTkLabel(row, text="", width=28)
        icon_label.pack(side="left", padx=(2, 0))

        gear_var = ctk.StringVar(value=default_option)

        def update_icon(v):
            try:
                gid = int(v.split(".")[0].strip())
                icon = get_gear_icon(gid)
                if icon:
                    icon_label.configure(image=icon)
            except Exception:
                pass

        def on_select(v):
            update_icon(v)
            self._emit()

        dropdown_btn = ctk.CTkButton(
            row, textvariable=gear_var, width=200, height=28,
            fg_color="#2b2b2b", hover_color="#3b3b3b",
            anchor="w", text_color="white",
            image=get_icon("down", 14),
            compound="right"
        )
        dropdown_btn.pack(side="left", padx=4)

        dropdown = ScrollableDropdown(
            dropdown_btn, avail_options, gear_var,
            on_select=on_select, max_visible=8
        )
        dropdown_btn.configure(command=dropdown.toggle)
        update_icon(default_option)

        def delete():
            row.destroy()
            self._equipped_rows = [(r, v) for r, v in self._equipped_rows if r != row]
            self._update_container_height(self._equipped_container, self._equipped_rows)
            self._emit()

        ctk.CTkButton(row, text="", image=get_icon("remove"), width=28, height=24,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=delete).pack(side="left", padx=4)

        self._equipped_rows.append((row, gear_var))
        self._update_container_height(self._equipped_container, self._equipped_rows)

    def _add_equipped_text(self, val: str = ""):
        """DB 없을 때 폴백 — 기존 텍스트 입력 방식"""
        row = ctk.CTkFrame(self._equipped_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        val_var = ctk.StringVar(value=val)
        ctk.CTkEntry(row, textvariable=val_var, width=100,
                     placeholder_text="장비 ID").pack(side="left", padx=2)

        def delete():
            row.destroy()
            self._equipped_rows = [(r, v) for r, v in self._equipped_rows if r != row]
            self._update_container_height(self._equipped_container, self._equipped_rows)
            self._emit()

        ctk.CTkButton(row, text="", image=get_icon("remove"), width=28, height=24,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=delete).pack(side="left", padx=4)

        val_var.trace_add("write", lambda *_: self._emit())
        self._equipped_rows.append((row, val_var))
        self._update_container_height(self._equipped_container, self._equipped_rows)

    # ─────────────────────────────────────────
    # 로드 / 저장
    # ─────────────────────────────────────────
    def load(self, conditions: dict):
        aff:str = conditions.get("affection", ">=0")
        for op in OPERATORS:
            if aff.startswith(op):
                self._aff_op.set(op)
                self._aff_val.set(aff[len(op):])
                break

        time_str = conditions.get("time", "00:00~23:59")
        if "~" in time_str:
            parts = time_str.split("~")
            self._time_start.set(parts[0].strip())
            self._time_end.set(parts[1].strip())

        stat = conditions.get("stat", {})
        for s in STATS:
            val = stat.get(s, ">=0")
            for op in OPERATORS:
                if val.startswith(op):
                    self._stat_ops[s].set(op)
                    self._stat_vals[s].set(val[len(op):])
                    break

        for r, *_ in self._flag_rows:
            r.destroy()
        self._flag_rows.clear()
        for key, val in conditions.get("flag", {}).items():
            op, v = ">=", val
            for o in OPERATORS:
                if val.startswith(o):
                    op, v = o, val[len(o):]
                    break
            self._add_flag(key, op, v)

        for r, *_ in self._equipped_rows:
            r.destroy()
        self._equipped_rows.clear()
        for eq_id in conditions.get("equipped", []):
            self._add_equipped(str(eq_id))

    def get_conditions(self) -> dict:
        flag = {}
        for _, key_var, op_var, val_var in self._flag_rows:
            k = key_var.get().strip()
            if k:
                flag[k] = f"{op_var.get()}{val_var.get()}"

        equipped = []
        for _, val_var in self._equipped_rows:
            v = val_var.get().strip()
            if v:
                try:
                    # "번호. 이름" 또는 순수 숫자 모두 처리
                    equipped.append(int(v.split(".")[0].strip()))
                except ValueError:
                    pass

        return {
            "flag": flag,
            "time": f"{self._time_start.get()}~{self._time_end.get()}",
            "affection": f"{self._aff_op.get()}{self._aff_val.get()}",
            "stat": {s: f"{self._stat_ops[s].get()}{self._stat_vals[s].get()}" for s in STATS},
            "equipped": equipped
        }

    def _emit(self):
        if self.on_change:
            self.on_change()