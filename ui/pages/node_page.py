import customtkinter as ctk
import json
from typing import Callable, List
from core.models import Node, Dialogue, Step, Button
from ui.components.step_editor import StepEditor
from ui.components.run_editor import RunEditor
from ui.components.button_editor import ButtonEditor
from utils.icons import get_icon, btn

class NodePage(ctk.CTkFrame):
    def __init__(self, parent, on_change: Callable = None, get_emotions: Callable = None, get_skins: Callable = None):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self.get_emotions = get_emotions
        self.get_skins = get_skins
        self._node: Node | None = None
        self._node_names: List[str] = []
        self._dlg_index: int = 0

        self._dlg_frames: list = []
        self._step_editors: list[StepEditor] = []
        self._btn_editors: list[ButtonEditor] = []
        self._run_editor: RunEditor | None = None

        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 0))

        self.node_label = ctk.CTkLabel(top, text="노드: -",
                                       font=ctk.CTkFont(size=14, weight="bold"))
        self.node_label.pack(side="left", padx=8)

        ctk.CTkButton(top, text="대사 추가", image=get_icon("plus"), width=110, height=28,
                      command=self._add_dialogue).pack(side="right", padx=4)
        ctk.CTkButton(top, text="대사 삭제", image=get_icon("remove"), width=110, height=28,
                      fg_color="#7a2d2d", hover_color="#5e2323",
                      command=self._delete_dialogue).pack(side="right", padx=4)

        self.dlg_tab_frame = ctk.CTkFrame(self, height=36, corner_radius=0)
        self.dlg_tab_frame.pack(fill="x", padx=8, pady=4)

        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=8, pady=4)

    # ─────────────────────────────────────────
    # 노드 로드
    # ─────────────────────────────────────────
    def load_node(self, node: Node, node_names: List[str]):
        # 현재 노드에 저장
        #self._save_current(target_node=self._node)
        # 저장 후 위젯 변수 무효화 (다음 _save_current 가 실행되지 않도록)
        if hasattr(self, 'dlg_id_var'):
            del self.dlg_id_var
        if hasattr(self, 'dlg_skin_var'):
            del self.dlg_skin_var

        self._node = node
        self._node_names = node_names
        self._dlg_index = 0
        self.node_label.configure(text=f"노드: {node.name}")
        self._refresh_dlg_tabs()
        if node.dialogues:
            self._load_dialogue(0)
        else:
            self._clear_scroll()

    def _refresh_dlg_tabs(self):
        for w in self.dlg_tab_frame.winfo_children():
            w.destroy()

        if not self._node:
            return

        for i, dlg in enumerate(self._node.dialogues):
            btn = ctk.CTkButton(
                self.dlg_tab_frame,
                text=dlg.id or f"대사{i+1}",
                width=100, height=28,
                fg_color=("#2b4f6e" if i == self._dlg_index else "transparent"),
                hover_color="#1e3a52",
                command=lambda idx=i: self._load_dialogue(idx)
            )
            btn.pack(side="left", padx=2, pady=3)

    def _load_dialogue(self, index: int):
        if not self._node or index >= len(self._node.dialogues):
            return
        # 저장 전 위젯 무효화
        if hasattr(self, 'dlg_id_var'):
            del self.dlg_id_var
        if hasattr(self, 'dlg_skin_var'):
            del self.dlg_skin_var

        self._dlg_index = index
        self._refresh_dlg_tabs()
        self._render_dialogue(self._node.dialogues[index])

    def _render_dialogue(self, dlg: Dialogue):
        self._clear_scroll()
        self.scroll.pack_forget()

        # ── 대사 기본 정보 ──
        info_frame = ctk.CTkFrame(self.scroll, corner_radius=6)
        info_frame.pack(fill="x", pady=4)

        row = ctk.CTkFrame(info_frame, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(row, text="대사 ID", width=70, anchor="e").pack(side="left", padx=4)
        self.dlg_id_var = ctk.StringVar(value=dlg.id)
        ctk.CTkEntry(row, textvariable=self.dlg_id_var, width=160).pack(side="left", padx=4)

        ctk.CTkLabel(row, text="상승 호감도", width=110, anchor="e").pack(side="left", padx=8)
        self.dlg_delta_var = ctk.StringVar(value=str(dlg.delta))
        ctk.CTkEntry(row, textvariable=self.dlg_delta_var, width=70).pack(side="left", padx=4)

        ctk.CTkLabel(row, text="특정 스킨 전용", width=80, anchor="e").pack(side="left", padx=8)

        # 스킨 목록: 모두 적용 + 기본 + 특수 스킨들
        skin_options = self._get_skin_options()
        self.dlg_skin_var = ctk.StringVar(value=dlg.skin if dlg.skin else "모두 적용")
        self.dlg_skin_menu = ctk.CTkOptionMenu(
            row, variable=self.dlg_skin_var,
            values=skin_options, width=130
        )
        self.dlg_skin_menu.pack(side="left", padx=4)

        ctk.CTkLabel(row, text="최대 횟수", width=110, anchor="e").pack(side="left", padx=8)
        self.dlg_chance_entry = ctk.CTkEntry(row, width=60,
                                              placeholder_text="무제한",
                                              placeholder_text_color="gray60")
        self.dlg_chance_entry.pack(side="left", padx=4)
        if dlg.chance is not None:
            self.dlg_chance_entry.insert(0, str(dlg.chance))

        # ── 조건 ──
        from ui.components.condition_editor import ConditionEditor
        from ui.components.tooltip import Tooltip

        self.cond_editor = ConditionEditor(
            self.scroll, conditions=dlg.conditions, on_change=None
        )
        self.cond_editor.pack(fill="x", pady=4)
        self.scroll.after(0, lambda: setattr(self.cond_editor, 'on_change', self._emit))

        # ── 대사 스텝 ──
        step_header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        step_header.pack(fill="x", pady=(8, 2))
        ctk.CTkLabel(step_header, text="대사 스텝",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)
        Tooltip(step_header,
            "캐릭터가 순서대로 출력할 대사 목록입니다.\n"
            "각 스텝마다 감정 이미지, 딜레이, 텍스트를\n"
            "설정할 수 있습니다."
        ).pack(side="left", padx=2)
        ctk.CTkButton(step_header, text="스텝 추가", image=get_icon("plus"),
                      width=100, height=26,
                      command=self._add_step).pack(side="right", padx=4)

        self.step_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.step_container.pack(fill="x")
        self._step_editors = []
        self._loading_steps = True  # ← 로딩 플래그

        for step in dlg.steps:
            self._append_step(step)

        self._loading_steps = False  # ← 완료

        # ── run 보상 ──
        self._run_editor = RunEditor(self.scroll, run=dlg.run, on_change=None)
        self._run_editor.pack(fill="x", pady=(12, 4))
        if self.get_skins:
            self._run_editor.set_skin_options(self.get_skins())
        self.scroll.after(0, lambda: setattr(self._run_editor, 'on_change', self._emit))

        # ── 버튼 ──
        btn_header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_header.pack(fill="x", pady=(12, 2))
        ctk.CTkLabel(btn_header, text="다음 선택지",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)
        Tooltip(btn_header,
            "이 대사 이후 플레이어에게 표시되는 선택지입니다.\n"
            "각 버튼마다 이동할 노드, 조건, 호감도 변화를\n"
            "설정할 수 있습니다.\n"
            "버튼이 없으면 대화가 자동으로 종료됩니다."
        ).pack(side="left", padx=2)
        ctk.CTkButton(btn_header, text="버튼 추가", image=get_icon("plus"),
                      width=100, height=26,
                      command=self._add_button).pack(side="right", padx=4)

        self.btn_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.btn_container.pack(fill="x", pady=4)
        self._btn_editors = []

        for btn in self._node.buttons:
            self._append_button(btn, emit=False)

        self.scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self.scroll.update_idletasks()

    # ─────────────────────────────────────────
    # 스텝 조작
    # ─────────────────────────────────────────
    def _append_step(self, step: Step = None):
        if step is None:
            step = Step()
        idx = len(self._step_editors)
        extra_emotions = self.get_emotions() if self.get_emotions else []
        editor = StepEditor(
            self.step_container, step,
            on_delete=self._delete_step,
            on_change=self._emit if not getattr(self, '_loading_steps', False) else None,
            index=idx,
            extra_emotions=extra_emotions
        )
        editor.pack(fill="x", pady=3)
        self._step_editors.append(editor)
        # 로딩 완료 후 on_change 연결
        if getattr(self, '_loading_steps', False):
            self.scroll.after(0, lambda e=editor: setattr(e, 'on_change', self._emit))
    def _add_step(self):
        self._append_step()

    def _delete_step(self, editor: StepEditor):
        editor.destroy()
        self._step_editors.remove(editor)
        self._emit()

    # ─────────────────────────────────────────
    # 버튼 조작
    # ─────────────────────────────────────────
    def _append_button(self, btn: Button = None, emit: bool = True):
        if btn is None:
            btn = Button(id=f"btn_{len(self._btn_editors)+1}", label="버튼", next="")
        idx = len(self._btn_editors)
        editor = ButtonEditor(
            self.btn_container, btn, self._node_names,
            on_delete=self._delete_button,
            on_change=self._emit,
            index=idx,
            get_skins=self.get_skins,
            current_node=self._node.name if self._node else ""
        )
        editor.pack(fill="x", pady=3)
        self._btn_editors.append(editor)
        if emit:
            self._emit()  # 새 버튼 추가 시에만

    def _add_button(self):
        self._append_button(emit=True)  # 사용자가 추가할 때만 emit

    def _delete_button(self, editor: ButtonEditor):
        editor.destroy()
        self._btn_editors.remove(editor)
        self._emit()

    # ─────────────────────────────────────────
    # 대사 추가/삭제
    # ─────────────────────────────────────────
    def _add_dialogue(self):
        if not self._node:
            return
        self._save_current(target_node=self._node)
        new_dlg = Dialogue(
            id=f"{self._node.name}_dlg{len(self._node.dialogues)+1}",
            steps=[Step()]
        )
        self._node.dialogues.append(new_dlg)
        self._dlg_index = len(self._node.dialogues) - 1
        self._refresh_dlg_tabs()
        self._render_dialogue(new_dlg)
        self._emit()

    def _delete_dialogue(self):
        if not self._node or not self._node.dialogues:
            return
        if len(self._node.dialogues) == 1:
            return
        self._node.dialogues.pop(self._dlg_index)
        self._dlg_index = max(0, self._dlg_index - 1)
        self._refresh_dlg_tabs()
        self._render_dialogue(self._node.dialogues[self._dlg_index])
        self._emit()

    # ─────────────────────────────────────────
    # 저장 / emit
    # ─────────────────────────────────────────
    def _clear_scroll(self):
        self.scroll.pack_forget()
        for w in self.scroll.winfo_children():
            w.destroy()
        self._step_editors = []
        self._btn_editors = []
        self._run_editor = None

    def _save_current(self, target_node: Node | None = None):
        node = target_node if target_node is not None else self._node
        if not node or not node.dialogues:
            return
        if self._dlg_index >= len(node.dialogues):
            return
        if not hasattr(self, 'dlg_id_var') or not hasattr(self, 'dlg_skin_var') or not hasattr(self, 'cond_editor'):
            return

        try:
            conditions = self.cond_editor.get_conditions()
        except Exception:
            conditions = {}

        skin_val = self.dlg_skin_var.get()
        skin = None if skin_val == "모두 적용" else skin_val
        try:
            chance_str = self.dlg_chance_entry.get().strip()
            chance = int(chance_str) if chance_str else None
        except ValueError:
            chance = None
        try:
            delta = int(self.dlg_delta_var.get())
        except ValueError:
            delta = 0

        dlg = Dialogue(
            id=self.dlg_id_var.get(),
            skin=skin,
            conditions=conditions,
            chance=chance,
            delta=delta,
            run=self._run_editor.get_run() if self._run_editor else {},
            steps=[e.get_step() for e in self._step_editors]
        )
        node.dialogues[self._dlg_index] = dlg
        node.buttons = [e.get_button() for e in self._btn_editors]

    def _emit(self):
        self._save_current(target_node=self._node)
        if self.on_change and self._node:
            self.on_change(self._node)

    # ─────────────────────────────────────────
    # 스킨 / skin
    # ─────────────────────────────────────────
    def _get_skin_options(self) -> list[str]:
        options = ["모두 적용", "기본"]
        # get_emotions 콜백에서 스킨 목록도 가져올 수 있으면 추가
        # 일단 node_names 에서 스킨 정보는 없으니 app에서 콜백 추가 필요
        if hasattr(self, 'get_skins') and self.get_skins:
            options += self.get_skins()
        return options