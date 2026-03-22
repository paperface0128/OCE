import customtkinter as ctk
from typing import Dict, Any, Callable
from utils.icons import get_icon


class RunEditor(ctk.CTkFrame):
    def __init__(self, parent, run: Dict[str, Any] = None, on_change: Callable = None):
        super().__init__(parent, corner_radius=6)
        self.on_change = None  # 빌드 중 emit 방지
        self._item_rows: list = []
        self._gear_rows: list = []
        self._expanded = False
        self._build(run or {})
        self.on_change = on_change  # 빌드 완료 후 연결

    def _build(self, run: dict):
        # ── 헤더 ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(header, text="보상",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        # 툴팁 추가
        from ui.components.tooltip import Tooltip
        Tooltip(header,
            "이 대사가 출력된 후 지급되는 보상입니다.\n"
            "페니(재화), 아이템, 장비를 지급 혹은 차감하거나\n"
            "캐릭터 스킨을 변경할 수 있습니다."
        ).pack(side="left", padx=4)

        self._toggle_btn = ctk.CTkButton(
            header, text="펼치기",
            image=get_icon("right", 14),
            compound="left",
            width=90, height=24,
            fg_color="transparent", hover_color="#2a2a2a",
            command=self._toggle
        )
        self._toggle_btn.pack(side="right", padx=4)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._build_content(run)

    def _build_content(self, run: dict):
        form = ctk.CTkFrame(self._content, fg_color="transparent")
        form.pack(fill="x", padx=30, pady=4)

        def lbl(text, r, c):
            ctk.CTkLabel(form, text=text, anchor="w").grid(
                row=r, column=c, padx=(0, 4), pady=4, sticky="w"
            )

        # ── 페니 ──
        lbl("페니", 0, 0)
        self.penny_var = ctk.StringVar(value=str(run.get("페니", "")) if "페니" in run else "")
        ctk.CTkEntry(form, textvariable=self.penny_var, width=100,
                     placeholder_text="비워두면 없음").grid(row=0, column=1, padx=(0, 20), pady=4, sticky="w")
        self.penny_var.trace_add("write", lambda *_: self._emit())

        # ── 스킨 변경 ──
        lbl("스킨 변경", 0, 2)
        skins = self._get_skin_options()
        current_skin = run.get("set_skin", "없음")
        if current_skin not in skins:
            current_skin = "없음"
        self.set_skin_var = ctk.StringVar(value=current_skin)
        ctk.CTkOptionMenu(
            form, variable=self.set_skin_var,
            values=skins, width=130,
            command=lambda _: self._emit()
        ).grid(row=0, column=3, padx=4, pady=4, sticky="w")


        # ── 아이템 ──
        item_header = ctk.CTkFrame(self._content, fg_color="transparent")
        item_header.pack(fill="x", padx=30, pady=(8, 0))
        ctk.CTkLabel(item_header, text="아이템",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(item_header, text="추가", image=get_icon("plus"), width=70, height=24,
                      command=self._add_item).pack(side="right")

        self._item_container = ctk.CTkFrame(self._content, fg_color="transparent", height=0)
        self._item_container.pack(fill="x", padx=30)
        self._item_container.pack_propagate(False)

        # ── 장비 ──
        gear_header = ctk.CTkFrame(self._content, fg_color="transparent")
        gear_header.pack(fill="x", padx=30, pady=(8, 0))
        ctk.CTkLabel(gear_header, text="장비",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(gear_header, text="추가", image=get_icon("plus"), width=70, height=24,
                      command=self._add_gear).pack(side="right")

        self._gear_container = ctk.CTkFrame(self._content, fg_color="transparent", height=0)
        self._gear_container.pack(fill="x", padx=30, pady=(0, 8))
        self._gear_container.pack_propagate(False)

        # 기존 run 로드
        item = run.get("아이템", None)
        if item and len(item) == 2:
            self._add_item(item[0], item[1])

        for gear_id in (run.get("장비", []) or []):
            self._add_gear(gear_id)

    def _get_skin_options(self) -> list[str]:
        # app 의 get_skins 콜백이 없으니 일단 없음만
        return ["없음"]

    def set_skin_options(self, skins: list[str]):
        options = ["없음"] + skins
        self.set_skin_var.set(self.set_skin_var.get() if self.set_skin_var.get() in options else "없음")
        # OptionMenu 업데이트는 재생성 필요 - 단순히 options 저장
        self._skin_options = options

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._content.pack(fill="x", padx=4, pady=(0, 8))
            self._toggle_btn.configure(image=get_icon("down", 14), text="접기")
        else:
            self._content.pack_forget()
            self._toggle_btn.configure(image=get_icon("right", 14), text="펼치기")

    def _update_height(self, container: ctk.CTkFrame, rows: list):
        if rows:
            container.configure(height=len(rows) * 36)
            container.pack_propagate(True)
        else:
            container.configure(height=0)
            container.pack_propagate(False)

    # ── 아이템 행 ──
    # ID 파싱: "4. 오래된 시계 부품" → 4
    def parse_id(self, val: str) -> int:
        """'4. 이름' 또는 '4 - 이름' 모두 파싱"""
        try:
            return int(val.split(".")[0].split("-")[0].strip())
        except Exception:
            return -1
    def _get_used_item_ids(self) -> set:
        used = set()
        for _, item_var, _ in self._item_rows:
            try:
                used.add(self.parse_id(item_var.get()))
            except Exception:
                pass
        return used

    def _get_used_gear_ids(self) -> set:
        used = set()
        for _, gear_var in self._gear_rows:
            try:
                used.add(self.parse_id(gear_var.get()))
            except Exception:
                pass
        return used
    def _add_item(self, item_id=None, count=None):
        from core.db_reader import get_items
        from core.icon_cache import get_item_icon
        from ui.components.scrollable_dropdown import ScrollableDropdown

        items = get_items()
        if not items:
            return

        used_ids = self._get_used_item_ids()
        # 기존에 지정된 item_id 는 사용 중으로 안 봄 (로드 시)
        if item_id:
            used_ids.discard(item_id)

        # 사용 중이지 않은 아이템만
        available = [i for i in items if i["id"] not in used_ids]
        if not available:
            return  # 더 추가할 아이템 없음

        row = ctk.CTkFrame(self._item_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        all_options = [f"{i['id']}. {i['name']}" for i in items]
        avail_options = [f"{i['id']}. {i['name']}" for i in available]

        default_id = item_id if item_id else available[0]["id"]
        default_option = next(
            (o for o in all_options if o.startswith(f"{default_id}.")), avail_options[0]
        )

        icon_label = ctk.CTkLabel(row, text="", width=28)
        icon_label.pack(side="left", padx=(2, 0))

        item_var = ctk.StringVar(value=default_option)

        def update_icon(val):
            try:
                iid = self.parse_id(val)
                icon = get_item_icon(iid)
                if icon:
                    icon_label.configure(image=icon)
            except Exception:
                pass

        def on_select(val):
            update_icon(val)
            self._emit()

        dropdown_btn = ctk.CTkButton(
            row, textvariable=item_var, width=200, height=28,
            fg_color="#2b2b2b", hover_color="#3b3b3b",
            anchor="w", text_color="white",
            image=get_icon("down", 14),
            compound="right"
        )
        dropdown_btn.pack(side="left", padx=4)

        # 드롭다운은 사용 중 제외한 옵션으로
        dropdown = ScrollableDropdown(
            dropdown_btn, avail_options, item_var,
            on_select=on_select, max_visible=8
        )
        dropdown_btn.configure(command=dropdown.toggle)
        update_icon(default_option)

        count_var = ctk.StringVar(value=str(count) if count else "1")
        ctk.CTkEntry(row, textvariable=count_var, width=60).pack(side="left", padx=4)
        count_var.trace_add("write", lambda *_: self._emit())

        def delete():
            row.destroy()
            self._item_rows = [(r, iv, cv) for r, iv, cv in self._item_rows if r != row]
            self._update_height(self._item_container, self._item_rows)
            self._emit()

        ctk.CTkButton(row, text="", image=get_icon("remove"), width=28, height=24,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=delete).pack(side="left", padx=2)

        self._item_rows.append((row, item_var, count_var))
        self._update_height(self._item_container, self._item_rows)

    def _add_gear(self, gear_id=None):
        from core.db_reader import get_gears
        from core.icon_cache import get_gear_icon
        from ui.components.scrollable_dropdown import ScrollableDropdown

        gears = get_gears()
        if not gears:
            return

        used_ids = self._get_used_gear_ids()
        if gear_id:
            used_ids.discard(gear_id)

        available = [g for g in gears if g["id"] not in used_ids]
        if not available:
            return

        row = ctk.CTkFrame(self._gear_container, fg_color="transparent")
        row.pack(fill="x", pady=2)

        all_options = [f"{g['id']}. {g['name']}" for g in gears]
        avail_options = [f"{g['id']}. {g['name']}" for g in available]

        default_id = gear_id if gear_id else available[0]["id"]
        default_option = next(
            (o for o in all_options if o.startswith(f"{default_id}.")), avail_options[0]
        )

        icon_label = ctk.CTkLabel(row, text="", width=28)
        icon_label.pack(side="left", padx=(2, 0))

        gear_var = ctk.StringVar(value=default_option)

        def update_icon(val):
            try:
                gid = self.parse_id(val)
                icon = get_gear_icon(gid)
                if icon:
                    icon_label.configure(image=icon)
            except Exception:
                pass

        def on_select(val):
            update_icon(val)
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
            self._gear_rows = [(r, gv) for r, gv in self._gear_rows if r != row]
            self._update_height(self._gear_container, self._gear_rows)
            self._emit()

        ctk.CTkButton(row, text="", image=get_icon("remove"), width=28, height=24,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=delete).pack(side="left", padx=2)

        self._gear_rows.append((row, gear_var))
        self._update_height(self._gear_container, self._gear_rows)

    def get_run(self) -> dict:
        run = {}

        # 페니
        try:
            p = self.penny_var.get().strip()
            if p:
                run["페니"] = int(p)
        except ValueError:
            pass

        # 스킨
        skin = self.set_skin_var.get().strip()
        if skin and skin != "없음":
            run["set_skin"] = skin

        # 아이템 (첫 번째만)
        if self._item_rows:
            _, item_var, count_var = self._item_rows[0]
            try:
                iid = int(item_var.get().split(".")[0].strip())
                cnt = int(count_var.get().strip())
                run["아이템"] = [iid, cnt]
            except Exception:
                pass

        # 장비
        gear_ids = []
        for _, gear_var in self._gear_rows:
            try:
                gid = int(gear_var.get().split(".")[0].strip())
                gear_ids.append(gid)
            except Exception:
                pass
        if gear_ids:
            run["장비"] = gear_ids

        return run

    def _emit(self):
        if self.on_change:
            self.on_change()