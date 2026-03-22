import customtkinter as ctk
import json
from core.models import Button
from utils.icons import get_icon, btn

BUTTON_COLORS = {
    "회색": "gray",
    "빨강": "red",
    "초록": "green",
    "파랑": "blurple",
}
BUTTON_COLORS_KR = list(BUTTON_COLORS.keys())

def color_to_kr(color: str) -> str:
    for kr, en in BUTTON_COLORS.items():
        if en == color:
            return kr
    return "회색"


class ButtonEditor(ctk.CTkFrame):
    def __init__(self, parent, btn: Button, node_names: list, on_delete=None, on_change=None, index=0, get_skins=None, current_node: str = ""):
        super().__init__(parent, corner_radius=6, border_width=1)
        self.on_delete = on_delete
        self.on_change = None
        self.index = index
        self.get_skins = get_skins
        self._current_node = current_node
        self._build(btn, node_names)
        self.on_change = on_change  # ← 빌드 완료 후 연결

    def _build(self, btn: Button, node_names: list):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 2))
        ctk.CTkLabel(header, text=f"버튼 {self.index + 1}",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(
            header, text="", image=get_icon("remove"), width=28, height=24,
            fg_color="#7a2d2d", hover_color="#5e2323",
            command=lambda: self.on_delete(self) if self.on_delete else None
        ).pack(side="right", padx=2)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=8, pady=(0, 4))

        def lbl(text, r, c, w=60):
            ctk.CTkLabel(body, text=text, width=w, anchor="e").grid(
                row=r, column=c, padx=(4, 2), pady=3, sticky="e"
            )

        lbl("ID", 0, 0)
        self.id_var = ctk.StringVar(value=btn.id)
        ctk.CTkEntry(body, textvariable=self.id_var, width=140).grid(row=0, column=1, padx=4, pady=3, sticky="w")
        self.id_var.trace_add("write", lambda *_: self._emit())

        lbl("라벨", 0, 2)
        self.label_var = ctk.StringVar(value=btn.label)
        ctk.CTkEntry(body, textvariable=self.label_var, width=140).grid(row=0, column=3, padx=4, pady=3, sticky="w")
        self.label_var.trace_add("write", lambda *_: self._emit())

        lbl("색상", 1, 0)
        self.color_var = ctk.StringVar(value=color_to_kr(btn.color))
        ctk.CTkOptionMenu(body, variable=self.color_var, values=BUTTON_COLORS_KR, width=100,
                          command=lambda _: self._emit()).grid(row=1, column=1, padx=4, pady=3, sticky="w")

        lbl("이동 노드", 1, 2, w=70)
        next_options = [n for n in node_names if n != self._current_node]
        if not next_options:
            next_options = ["노드가 없습니다."]
            next_state = "disabled"
            default_next = "노드가 없습니다."
        else:
            next_state = "normal"
            default_next = btn.next if btn.next and btn.next in next_options else next_options[0]
        self.next_var = ctk.StringVar(value=default_next)
        ctk.CTkOptionMenu(body, variable=self.next_var, values=next_options,
                          width=130, state=next_state,
                          command=lambda _: self._emit()).grid(row=1, column=3, padx=4, pady=3, sticky="w")

        lbl("특정 스킨 전용", 2, 0, w=90)
        skin_options = self._get_skin_options()
        current_skin = btn.skin if btn.skin else "모두 적용"
        if current_skin not in skin_options:
            current_skin = "모두 적용"
        self.skin_var = ctk.StringVar(value=current_skin)
        ctk.CTkOptionMenu(body, variable=self.skin_var, values=skin_options,
                          width=130, command=lambda _: self._emit()).grid(
            row=2, column=1, padx=4, pady=3, sticky="w"
        )

        body.columnconfigure(1, weight=1)
        body.columnconfigure(3, weight=1)

        # ── 조건 (grid 밖, 하단 별도) ──
        from ui.components.condition_editor import ConditionEditor
        self.cond_editor = ConditionEditor(
            self, conditions=btn.conditions, on_change=None
        )
        self.cond_editor.pack(fill="x", padx=8, pady=(0, 6))
        self.after(0, lambda: setattr(self.cond_editor, 'on_change', self._emit))


        body.columnconfigure(1, weight=1)
        body.columnconfigure(3, weight=1)

    def _get_skin_options(self) -> list[str]:
        options = ["모두 적용", "기본"]
        if self.get_skins:
            options += self.get_skins()
        return options

    def get_button(self) -> Button:
        try:
            conditions = self.cond_editor.get_conditions()
        except Exception:
            conditions = {}

        skin_val = self.skin_var.get()
        skin = None if skin_val == "모두 적용" else skin_val

        return Button(
            id=self.id_var.get(),
            skin=skin,
            label=self.label_var.get(),
            color=BUTTON_COLORS.get(self.color_var.get(), "gray"),
            next=self.next_var.get(),
            conditions=conditions,
            chance=None
        )

    def _emit(self):
        if self.on_change:
            self.on_change()