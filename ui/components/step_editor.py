import customtkinter as ctk
from core.models import Step
from utils.icons import get_icon, btn


class StepEditor(ctk.CTkFrame):
    def __init__(self, parent, step: Step, on_delete=None, on_change=None, index=0, extra_emotions: list = None):
        super().__init__(parent, corner_radius=6, border_width=1)
        self.on_delete = on_delete
        self.on_change = None
        self.index = index
        self._extra_emotions = extra_emotions or []
        self._build(step)
        self.on_change = on_change

    def _build(self, step: Step):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 2))

        ctk.CTkLabel(header, text=f"스텝 {self.index + 1}",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        ctk.CTkButton(
            header, text="", image=get_icon("remove"), width=28, height=24,
            fg_color="#7a2d2d", hover_color="#5e2323",
            command=lambda: self.on_delete(self) if self.on_delete else None
        ).pack(side="right", padx=2)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkLabel(body, text="감정", width=50, anchor="e").grid(row=0, column=0, padx=(0, 4), pady=4)

        if self._extra_emotions:
            in_list = step.emotion in self._extra_emotions
            self.emotion_var = ctk.StringVar(
                value=step.emotion if in_list else self._extra_emotions[0]
            )
            ctk.CTkOptionMenu(
                body, variable=self.emotion_var,
                values=self._extra_emotions, width=150,
                command=lambda _: self._emit()
            ).grid(row=0, column=1, padx=4, pady=4, sticky="w")
        else:
            self.emotion_var = ctk.StringVar(value="")
            ctk.CTkOptionMenu(
                body, values=["감정이 없습니다"],
                width=160, state="disabled"
            ).grid(row=0, column=1, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(body, text="딜레이(초)", width=70, anchor="e").grid(row=0, column=2, padx=(8, 4), pady=4)
        self.delay_var = ctk.StringVar(value=str(step.delay))
        ctk.CTkEntry(body, textvariable=self.delay_var, width=50).grid(
            row=0, column=3, padx=4, pady=4, sticky="w"
        )
        self.delay_var.trace_add("write", lambda *_: self._emit())

        ctk.CTkLabel(body, text="대사", width=50, anchor="e").grid(row=1, column=0, padx=(0, 4), pady=4, sticky="n")
        self.text_box = ctk.CTkTextbox(body, height=60, width=500)
        self.text_box.grid(row=1, column=1, columnspan=3, padx=4, pady=4, sticky="ew")
        self.text_box.insert("1.0", step.text)
        self.text_box.bind("<KeyRelease>", lambda _: self._emit())

        body.columnconfigure(1, weight=1)

    def get_step(self) -> Step:
        try:
            delay = int(self.delay_var.get())
        except ValueError:
            delay = 2
        return Step(
            delay=delay,
            emotion=self.emotion_var.get(),
            text=self.text_box.get("1.0", "end-1c")
        )

    def _emit(self):
        if self.on_change:
            self.on_change()