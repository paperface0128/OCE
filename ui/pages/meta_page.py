import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import Callable
from pathlib import Path
import shutil
import random
from core.models import CharacterMeta, SkinConfig
from utils.icons import get_icon, btn

def generate_character_id() -> int:
    return random.randint(10**19, 10**20 - 1)


class MetaPage(ctk.CTkFrame):
    def __init__(self, parent, on_change: Callable = None, get_save_path: Callable = None):
        super().__init__(parent, fg_color="transparent")
        self.on_change = on_change
        self.get_save_path = get_save_path
        self._meta = CharacterMeta()
        self._skin_rows: list = []
        self._character_id: int = generate_character_id()
        self._is_saved: bool = False
        self._build()

    def _build(self):
        # ── 상단 스크롤 영역 (감정 이미지 제외) ──
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="x")
        # 창 크기 변경 시 scroll 높이 동적 조정
        def _on_resize(e):
            h = max(300, e.height // 2)
            self._scroll.configure(height=h)

        self.bind("<Configure>", _on_resize)
        ctk.CTkLabel(self._scroll, text="캐릭터 기본 정보",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))

        form = ctk.CTkFrame(self._scroll)
        form.pack(fill="x", padx=16, pady=4)

        def lbl(text, r):
            ctk.CTkLabel(form, text=text, width=100, anchor="e").grid(
                row=r, column=0, padx=(8, 4), pady=6, sticky="e"
            )

        lbl("캐릭터 ID", 0)
        id_frame = ctk.CTkFrame(form, fg_color="transparent")
        id_frame.grid(row=0, column=1, padx=4, pady=6, sticky="w")
        self.id_label = ctk.CTkLabel(id_frame, text=str(self._character_id),
                                      text_color="gray", font=ctk.CTkFont(size=11))
        self.id_label.pack(side="left", padx=(0, 8))
        self.regen_btn = ctk.CTkButton(id_frame, text="재설정", width=80, height=24,
                                        command=self._regenerate_id)
        self.regen_btn.pack(side="left")

        lbl("이름 *", 1)
        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(form, textvariable=self.name_var, width=200,
                                        placeholder_text="필수 입력")
        self.name_entry.grid(row=1, column=1, padx=4, pady=6, sticky="w")
        self.name_var.trace_add("write", lambda *_: self._on_name_change())

        lbl("설명", 2)
        self.desc_entry = ctk.CTkEntry(form, width=360)
        self.desc_entry.grid(row=2, column=1, padx=4, pady=6, sticky="w")

        lbl("아이콘(이모지)", 3)

        icon_row = ctk.CTkFrame(form, fg_color="transparent")
        icon_row.grid(row=3, column=1, padx=4, pady=6, sticky="w", columnspan=3)

        ctk.CTkLabel(icon_row, text=":", text_color="gray60",
                     font=ctk.CTkFont(size=14)).pack(side="left")

        self.icon_var = ctk.StringVar(value="question")
        icon_entry = ctk.CTkEntry(icon_row, textvariable=self.icon_var, width=120,
                                   placeholder_text="sob, heart, star...")
        icon_entry.pack(side="left", padx=2)

        ctk.CTkLabel(icon_row, text=":", text_color="gray60",
                     font=ctk.CTkFont(size=14)).pack(side="left")

        self._icon_preview_lbl = ctk.CTkLabel(icon_row, text="♥️", width=36,
                                               font=ctk.CTkFont(size=20))
        self._icon_preview_lbl.pack(side="left", padx=(8, 0))

        def _on_icon_change(*_):
            val = self.icon_var.get().strip()
            try:
                import emoji
                converted = emoji.emojize(f":{val}:", language="alias")
                if converted != f":{val}:":
                    self._icon_preview_lbl.configure(text=converted)
                else:
                    self._icon_preview_lbl.configure(text="알 수 없음")
            except ImportError:
                self._icon_preview_lbl.configure(text="알 수 없음")
            self._emit()

        self.icon_var.trace_add("write", _on_icon_change)

        ctk.CTkLabel(form, text="ex) :ribbon: :heart: :star: (디스코드 이모지 이름을 쓰세요)",
                     text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(
            row=3, column=3, padx=4, pady=6, sticky="w"
        )

        # ── 스킨 목록 ──
        self.default_skin_var = ctk.StringVar(value="기본")
        skin_header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        skin_header.pack(fill="x", padx=16, pady=(16, 2))
        ctk.CTkLabel(skin_header, text="스킨 목록",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        from ui.components.tooltip import Tooltip
        Tooltip(skin_header,
            "캐릭터의 스킨 종류:\n\n"
            "• normal — 보상의 스킨 변경을 통해서만 바뀌는 스킨입니다.\n"
            "  플레이어가 특정 조건을 달성하거나 이벤트를 통해 획득합니다.\n\n"
            "• season — 설정된 기간(MM-DD ~ MM-DD) 동안\n"
            "  자동으로 강제 적용되는 스킨입니다.\n"
            "  예: 크리스마스 스킨 (12-24 ~ 12-26)\n\n"
            "스킨 이미지는 아래 감정 이미지 관리에서 추가할 수 있습니다."
        ).pack(side="left", padx=6)

        ctk.CTkButton(skin_header, text="스킨 추가", image=get_icon("plus"), command=self._add_skin,
                      width=100, height=28).pack(side="right")

        self.skin_frame = ctk.CTkFrame(self._scroll)
        self.skin_frame.pack(fill="x", padx=16, pady=4)

        self.skin_empty_label = ctk.CTkLabel(
            self.skin_frame, text="추가된 스킨이 없습니다.",
            text_color="gray"
        )
        self.skin_empty_label.pack(pady=8)

        # ── 감정 이미지 관리 ──
        emotion_title_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        emotion_title_frame.pack(anchor="w", fill="x", padx=16, pady=(20, 4))

        ctk.CTkLabel(emotion_title_frame, text="감정 이미지 관리",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        Tooltip(emotion_title_frame,
            "캐릭터의 감정 이미지 관리 규칙:\n\n"
            "• 기본 스킨에 감정을 먼저 추가해야 합니다.\n"
            "• 특수 스킨은 기본 스킨에 있는 감정만 사용 가능합니다.\n"
            "• 특수 스킨에 감정 이미지가 없으면 기본 스킨 이미지가 사용됩니다.\n\n"
            "파일 구조:\n"
            "  images/기본/기쁨.png  ← 기본 스킨\n"
            "  images/여름/기쁨.png  ← 특수 스킨 (같은 감정 이름)\n\n"
            "대사 스텝에서 감정을 선택하면\n"
            "현재 캐릭터 스킨에 맞는 이미지가 자동으로 표시됩니다."
        ).pack(side="left", padx=6)

        # 기본 스킨 감정 추가
        base_frame = ctk.CTkFrame(self._scroll, corner_radius=6)
        base_frame.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(base_frame, text="감정 및 표정 추가",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))

        add_row = ctk.CTkFrame(base_frame, fg_color="transparent")
        add_row.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(add_row, text="감정 이름", width=60).pack(side="left", padx=(4, 4))
        self.emotion_name_var = ctk.StringVar()
        ctk.CTkEntry(add_row, textvariable=self.emotion_name_var, width=100,
                     placeholder_text="예: 기쁨").pack(side="left", padx=4)
        ctk.CTkButton(add_row, text="이미지 선택 & 추가", image=get_icon("save"), width=150,
                      command=lambda: self._add_emotion_image("기본")).pack(side="left", padx=12)

        # 특수 스킨 감정 이미지 교체
        special_frame = ctk.CTkFrame(self._scroll, corner_radius=6)
        special_frame.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(special_frame, text="스킨 감정 및 표정 할당",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))

        ctk.CTkLabel(special_frame,
                     text="기본 스킨에 있는 감정만 선택 가능합니다.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=(0, 4))

        self._special_row = ctk.CTkFrame(special_frame, fg_color="transparent")
        self._special_row.pack(fill="x", padx=8, pady=(0, 8))

        self._skin_lbl = ctk.CTkLabel(self._special_row, text="스킨", width=40)
        self._skin_lbl.pack(side="left", padx=(4, 4))

        self.special_skin_var = ctk.StringVar(value="스킨을 먼저 추가하세요")
        self.special_skin_menu = ctk.CTkOptionMenu(
            self._special_row, variable=self.special_skin_var,
            values=["스킨을 먼저 추가하세요"],
            width=140, state="disabled"
        )
        self.special_skin_menu.pack(side="left", padx=4)

        self._emotion_lbl = ctk.CTkLabel(self._special_row, text="감정", width=40)
        self._emotion_lbl.pack(side="left", padx=(8, 4))

        self.special_emotion_var = ctk.StringVar(value="먼저 기본 스킨 감정을 추가하세요")
        self.special_emotion_menu = ctk.CTkOptionMenu(
            self._special_row, variable=self.special_emotion_var,
            values=["먼저 기본 스킨 감정을 추가하세요"],
            width=200, state="disabled"
        )
        self.special_emotion_menu.pack(side="left", padx=4)

        ctk.CTkButton(self._special_row, text="이미지 선택 & 교체", image=get_icon("save"), width=150,
                      command=self._replace_special_emotion).pack(side="left", padx=12)
        # ── 구분선 ──
        ctk.CTkFrame(self, height=2, fg_color="#333333").pack(fill="x", padx=0, pady=0)
        # ── 현재 감정 이미지 — scroll 밖 ──
        emotion_header = ctk.CTkFrame(self, fg_color="transparent")
        emotion_header.pack(fill="x", padx=16, pady=(8, 2))
        ctk.CTkLabel(emotion_header, text="현재 감정 이미지",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(emotion_header, text="새로고침", image=get_icon("replay"), width=90, height=26,
                      command=self._refresh_emotion_list).pack(side="right")

        # ← MetaPage 직접 자식 — expand=True 로 남은 공간 전부
        self.emotion_list_frame = ctk.CTkScrollableFrame(self)
        self.emotion_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.emotion_list_frame.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        self.emotion_list_frame._parent_canvas.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        for w in self.emotion_list_frame.winfo_children():
            w.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
    # ─────────────────────────────────────────
    # ID 재생성
    # ─────────────────────────────────────────
    def _regenerate_id(self):
        if self._is_saved:
            messagebox.showwarning("불가", "이미 저장된 캐릭터의 ID는 변경할 수 없습니다.")
            return
        self._character_id = generate_character_id()
        self.id_label.configure(text=str(self._character_id))
        self._emit()

    def _on_name_change(self):
        name = self.name_var.get().strip()
        if name:
            self.name_entry.configure(border_color=("gray60", "gray40"))
        else:
            self.name_entry.configure(border_color="red")
        self._emit()

    # ─────────────────────────────────────────
    # 이미지 경로
    # ─────────────────────────────────────────
    def _get_image_base(self) -> Path | None:
        save_path = self.get_save_path() if self.get_save_path else None
        if not save_path:
            return None
        return Path(save_path) / "images"

    def _add_emotion_image(self, skin: str):
        save_path = self.get_save_path() if self.get_save_path else None
        if not save_path:
            messagebox.showwarning("경고", "먼저 프로젝트를 저장해서 캐릭터 폴더를 만들어주세요.")
            return

        name = self.emotion_name_var.get().strip()
        if not name:
            messagebox.showerror("오류", "감정 이름을 입력해주세요.")
            return

        # ── 플랜별 감정 수 제한 ──
        from core.auth import get_saved_auth, refresh_plan
        auth = get_saved_auth()
        plan = "free"
        if auth:
            plan = refresh_plan(auth["user_id"])

        PLAN_LIMITS = {
            "free": 5,
            "스타터": 8,
            "컬렉터": None  # 무제한
        }
        limit = PLAN_LIMITS.get(plan, 5)

        if limit is not None:
            # 기본 스킨 기준으로 현재 감정 수 계산
            base_dir = Path(save_path) / "images" / "기본"
            current_count = len(list(base_dir.glob("*.png"))) if base_dir.exists() else 0

            # 기본 스킨에 추가할 때만 체크
            if skin == "기본" and current_count >= limit:
                plan_names = {"free": "무료", "스타터": "스타터"}
                messagebox.showerror(
                    "감정 추가 불가",
                    f"현재 플랜({plan_names.get(plan, plan)})에서는\n"
                    f"감정 이미지를 최대 {limit}개까지 추가할 수 있습니다.\n\n"
                    f"더 많은 감정을 추가하려면 플랜을 업그레이드하세요.\n\n"
                    "플랜을 업그레이드하기 위해서는 [서포트 서버]를 눌러 서버에 참여한 뒤, 상품을 구매해주세요."
                )
                return

        src = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=[("PNG 이미지", "*.png")]
        )
        if not src:
            return

        dest_dir = Path(save_path) / "images" / skin
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{name}.png"

        if dest.exists():
            if not messagebox.askyesno("덮어쓰기", f"{name}.png 가 이미 존재합니다. 덮어쓸까요?"):
                return

        shutil.copy2(src, dest)
        messagebox.showinfo("완료", f"images/{skin}/{name}.png 추가 완료!")
        self.emotion_name_var.set("")
        self._refresh_emotion_list()
        self._update_special_emotion_menu()

    def _replace_special_emotion(self):
        save_path = self.get_save_path() if self.get_save_path else None
        if not save_path:
            messagebox.showwarning("경고", "먼저 프로젝트를 저장해주세요.")
            return

        skin = self.special_skin_var.get().strip()
        emotion = self.special_emotion_var.get().strip()

        if not skin:
            messagebox.showerror("오류", "스킨 이름을 입력해주세요.")
            return
        if not emotion or emotion == "먼저 기본 스킨 감정을 추가하세요":
            messagebox.showerror("오류", "감정을 선택해주세요.")
            return

        # 기본 스킨에 해당 감정 있는지 확인
        base_img = Path(save_path) / "images" / "기본" / f"{emotion}.png"
        if not base_img.exists():
            messagebox.showerror("오류", f"기본 스킨에 '{emotion}' 감정이 없습니다.")
            return

        src = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=[("PNG 이미지", "*.png")]
        )
        if not src:
            return

        dest_dir = Path(save_path) / "images" / skin
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{emotion}.png"

        if dest.exists():
            if not messagebox.askyesno("덮어쓰기", f"{skin}/{emotion}.png 가 이미 존재합니다. 덮어쓸까요?"):
                return

        shutil.copy2(src, dest)
        messagebox.showinfo("완료", f"images/{skin}/{emotion}.png 교체 완료!")
        self._refresh_emotion_list()

    def _update_special_emotion_menu(self):
        save_path = self.get_save_path() if self.get_save_path else None

        if not save_path:
            # 저장 경로 없으면 완전 초기화
            self.special_emotion_menu.configure(
                values=["먼저 기본 스킨 감정을 추가하세요"],
                state="disabled"
            )
            self.special_emotion_var.set("먼저 기본 스킨 감정을 추가하세요")
            return

        base = Path(save_path) / "images" / "기본"
        if not base.exists():
            self.special_emotion_menu.configure(
                values=["먼저 기본 스킨 감정을 추가하세요"],
                state="disabled"
            )
            self.special_emotion_var.set("먼저 기본 스킨 감정을 추가하세요")
            return

        emotions = sorted([p.stem for p in base.glob("*.png")])
        if emotions:
            self.special_emotion_menu.configure(values=emotions, state="normal")
            self.special_emotion_var.set(emotions[0])
        else:
            self.special_emotion_menu.configure(
                values=["먼저 기본 스킨 감정을 추가하세요"],
                state="disabled"
            )
            self.special_emotion_var.set("먼저 기본 스킨 감정을 추가하세요")

    def get_skin_names(self) -> list[str]:
        """추가된 특수 스킨 이름 목록 반환 — UI + 이미지 폴더 둘 다"""
        # UI 에 추가된 스킨
        ui_skins = [nv.get() for _, nv, *_ in self._skin_rows if nv.get().strip()]

        # 이미지 폴더에 있는 스킨도 포함
        base = self._get_image_base()
        folder_skins = []
        if base and base.exists():
            folder_skins = [
                d.name for d in base.iterdir()
                if d.is_dir() and d.name != "기본"
            ]

        # 합치기 (중복 제거, 순서 유지)
        seen = set()
        result = []
        for name in ui_skins + folder_skins:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result

    def _update_special_skin_menu(self):
        skins = self.get_skin_names()
        current = self.special_skin_var.get()

        self.special_skin_menu.destroy()

        if skins:
            if current not in skins:
                self.special_skin_var.set(skins[0])
            self.special_skin_menu = ctk.CTkOptionMenu(
                self._special_row, variable=self.special_skin_var,
                values=skins, width=140
            )
        else:
            self.special_skin_var.set("스킨을 먼저 추가하세요")
            self.special_skin_menu = ctk.CTkOptionMenu(
                self._special_row, variable=self.special_skin_var,
                values=["스킨을 먼저 추가하세요"],
                width=140, state="disabled"
            )

        self.special_skin_menu.pack(side="left", padx=4, before=self._emotion_lbl)
    # ─────────────────────────────────────────
    # 감정 목록 표시 (이름 변경 + 삭제 포함)
    # ─────────────────────────────────────────
    def _refresh_emotion_list(self):
        for w in self.emotion_list_frame.winfo_children():
            w.destroy()

        base = self._get_image_base()
        if not base:
            ctk.CTkLabel(self.emotion_list_frame,
                         text="프로젝트를 저장하면 이미지 목록이 표시됩니다.",
                         text_color="gray").pack(pady=8)
            return

        if not base.exists():
            ctk.CTkLabel(self.emotion_list_frame,
                         text="이미지 폴더가 없습니다. 이미지를 추가해보세요.",
                         text_color="gray").pack(pady=8)
            return

        try:
            from PIL import Image
            has_pil = True
        except ImportError:
            has_pil = False

        # 기본 스킨 감정 목록 먼저 수집
        base_emotions = []
        base_skin_dir = base / "기본"
        if base_skin_dir.exists():
            base_emotions = sorted([p.stem for p in base_skin_dir.glob("*.png")])

        found = False
        for skin_dir in sorted(base.iterdir()):
            if not skin_dir.is_dir():
                continue
            pngs = sorted(skin_dir.glob("*.png"))
            if not pngs:
                continue

            found = True
            ctk.CTkLabel(self.emotion_list_frame,
                         image=get_icon("save"),
                         text=f"  {skin_dir.name}",
                         compound="left",
                         font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(10, 4))

            row_frame = ctk.CTkFrame(self.emotion_list_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=8, pady=2)

            # 기본 스킨이면 그냥 순서대로
            if skin_dir.name == "기본":
                for png in pngs:
                    self._build_emotion_card(row_frame, png, has_pil)
            else:
                # 기본 감정 순서에 맞춰 빈 칸 포함 배치
                png_map = {p.stem: p for p in pngs}
                for emotion_name in base_emotions:
                    if emotion_name in png_map:
                        self._build_emotion_card(row_frame, png_map[emotion_name], has_pil)
                    else:
                        # 빈 칸 (해당 감정 없음)
                        self._build_empty_card(row_frame)

        if not found:
            lbl = ctk.CTkLabel(self.emotion_list_frame,
                         text="아직 이미지가 없습니다.",
                         text_color="gray")
            lbl.pack(pady=8)
            lbl.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        for w in self.emotion_list_frame.winfo_children():
            w.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        self._update_special_emotion_menu()
        self._update_special_skin_menu()

    def _on_emotion_scroll(self, event):
        self.emotion_list_frame._parent_canvas.yview_scroll(
            int(-1 * (event.delta / 5)), "units"
        )
        return "break"
    def _build_emotion_card(self, parent, png: Path, has_pil: bool):
        CARD_SIZE = 108  # 카드 크기 고정
        IMG_SIZE = 80    # 이미지 표시 영역 크기

        parent.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        card = ctk.CTkFrame(parent, corner_radius=6, width=CARD_SIZE, height=CARD_SIZE + 50)
        card.pack(side="left", padx=4, pady=2)
        card.pack_propagate(False)
        card.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        # 이미지 영역 — 1:1 고정 크기
        img_frame = ctk.CTkFrame(card, width=IMG_SIZE, height=IMG_SIZE,
                                  fg_color="transparent")
        img_frame.pack(pady=(6, 2))
        img_frame.pack_propagate(False)
        img_frame.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        if has_pil:
            try:
                from PIL import Image
                img = Image.open(png).convert("RGBA")

                # 원본 비율 유지하며 IMG_SIZE 안에 맞추기
                img.thumbnail((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

                # 1:1 캔버스에 중앙 배치
                canvas = Image.new("RGBA", (IMG_SIZE, IMG_SIZE), (0, 0, 0, 0))
                offset_x = (IMG_SIZE - img.width) // 2
                offset_y = (IMG_SIZE - img.height) // 2
                canvas.paste(img, (offset_x, offset_y), img)

                ctk_img = ctk.CTkImage(light_image=canvas, dark_image=canvas,
                                       size=(IMG_SIZE, IMG_SIZE))
                lbl = ctk.CTkLabel(img_frame, image=ctk_img, text="")
                lbl.image = ctk_img
                lbl.pack(expand=True)
                lbl.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
            except Exception:
                lbl = ctk.CTkLabel(img_frame, text="🖼", font=ctk.CTkFont(size=28))
                lbl.pack(expand=True)
                lbl.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        else:
            lbl = ctk.CTkLabel(img_frame, text="🖼", font=ctk.CTkFont(size=28))
            lbl.pack(expand=True)
            lbl.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        name_bar = ctk.CTkFrame(card, fg_color="#1e3a52", corner_radius=4)
        name_bar.pack(fill="x", padx=4, pady=(0, 2))
        name_bar.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        name_lbl = ctk.CTkLabel(name_bar, text=png.stem,
                     font=ctk.CTkFont(size=11), text_color="white")
        name_lbl.pack(pady=2)
        name_lbl.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 4))
        btn_row.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        ctk.CTkButton(
            btn_row, text="", image=get_icon("edit"), width=48, height=22,
            command=lambda p=png: self._rename_emotion(p)
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            btn_row, text="", image=get_icon("remove"), width=48, height=22,
            fg_color="#7a2d2d", hover_color="#5e2323",
            command=lambda p=png: self._delete_emotion(p)
        ).pack(side="left", padx=1)
    def _build_empty_card(self, parent):
        CARD_SIZE = 108
        parent.bind("<MouseWheel>", self._on_emotion_scroll, add="+")
        card = ctk.CTkFrame(parent, corner_radius=6, width=CARD_SIZE, height=CARD_SIZE + 50,
                            fg_color="transparent", border_width=1,
                            border_color="gray30")
        card.pack(side="left", padx=4, pady=2)
        card.pack_propagate(False)
        card.bind("<MouseWheel>", self._on_emotion_scroll, add="+")

        ctk.CTkLabel(card, text="—", text_color="gray40",
                     font=ctk.CTkFont(size=20)).place(relx=0.5, rely=0.5, anchor="center")
    def _rename_emotion(self, png: Path):
        dialog = ctk.CTkInputDialog(
            text=f"'{png.stem}' 의 새 이름을 입력하세요:",
            title="감정 이름 변경"
        )
        new_name = dialog.get_input()
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        new_path = png.parent / f"{new_name}.png"
        if new_path.exists():
            messagebox.showerror("오류", f"'{new_name}.png' 가 이미 존재합니다.")
            return
        png.rename(new_path)
        self._refresh_emotion_list()

    def _delete_emotion(self, png: Path):
        if not messagebox.askyesno("삭제 확인", f"'{png.stem}.png' 를 삭제할까요?\n이 작업은 되돌릴 수 없습니다."):
            return
        png.unlink()
        self._refresh_emotion_list()

    def get_emotions(self) -> list[str]:
        base = self._get_image_base()
        if not base or not base.exists():
            return []
        emotions = set()
        for skin_dir in base.iterdir():
            if skin_dir.is_dir():
                for png in skin_dir.glob("*.png"):
                    emotions.add(png.stem)
        return sorted(emotions)

    # ─────────────────────────────────────────
    # 스킨 행
    # ─────────────────────────────────────────
    def _add_skin(self, skin: SkinConfig = None):
        if skin is None:
            skin = SkinConfig(name="새스킨", skin_type="normal")

        self.skin_empty_label.pack_forget()

        row_frame = ctk.CTkFrame(self.skin_frame, corner_radius=6)
        row_frame.pack(fill="x", padx=4, pady=3)

        name_var = ctk.StringVar(value=skin.name)
        type_var = ctk.StringVar(value=skin.skin_type)
        enabled_var = ctk.BooleanVar(value=skin.enabled)
        start_var = ctk.StringVar(value=skin.period_start)
        end_var = ctk.StringVar(value=skin.period_end)

        ctk.CTkLabel(row_frame, text="이름", width=40).pack(side="left", padx=(8, 2))

        name_entry = ctk.CTkEntry(row_frame, textvariable=name_var, width=100)
        name_entry.pack(side="left", padx=2)

        # 중복 이름 체크
        def on_name_change(*_):
            current = name_var.get().strip()
            # 현재 행 제외하고 다른 행의 이름과 비교
            others = [nv.get().strip() for f, nv, *_ in self._skin_rows if f != row_frame]
            if current in others and current:
                name_entry.configure(border_color="red")
            else:
                name_entry.configure(border_color=("gray60", "gray40"))
            self._emit()

        name_var.trace_add("write", on_name_change)

        ctk.CTkLabel(row_frame, text="유형", width=40).pack(side="left", padx=(8, 2))
        type_menu = ctk.CTkOptionMenu(
            row_frame, variable=type_var,
            values=["normal", "season"], width=90,
            command=lambda v, sf=row_frame, sv=start_var, ev=end_var: self._toggle_period(sf, v, sv, ev)
        )
        type_menu.pack(side="left", padx=2)

        ctk.CTkCheckBox(row_frame, text="활성", variable=enabled_var, width=60).pack(side="left", padx=6)

        period_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        period_frame.pack(side="left", padx=4)
        ctk.CTkLabel(period_frame, text="기간", width=35).pack(side="left")
        ctk.CTkEntry(period_frame, textvariable=start_var, width=65, placeholder_text="MM-DD").pack(side="left", padx=2)
        ctk.CTkLabel(period_frame, text="~").pack(side="left")
        ctk.CTkEntry(period_frame, textvariable=end_var, width=65, placeholder_text="MM-DD").pack(side="left", padx=2)

        if skin.skin_type != "season":
            period_frame.pack_forget()

        def delete_row():
            row_frame.destroy()
            self._skin_rows = [(f, nv, tv, ev2, sv2, ev3) for f, nv, tv, ev2, sv2, ev3 in self._skin_rows if f != row_frame]
            if not self._skin_rows:
                self.skin_empty_label.pack(pady=8)
            self._update_special_skin_menu()
            self._emit()

        ctk.CTkButton(row_frame, text="", image=get_icon("remove"), width=32, fg_color="#7a2d2d",
                      hover_color="#5e2323", command=delete_row).pack(side="right", padx=6)

        self._skin_rows.append((row_frame, name_var, type_var, enabled_var, start_var, end_var))

        for var in [type_var, enabled_var, start_var, end_var]:
            var.trace_add("write", lambda *_: self._emit())

        name_var.trace_add("write", lambda *_: self._update_special_skin_menu())
        self._update_special_skin_menu()

    def _toggle_period(self, row_frame, value, start_var, end_var):
        for child in row_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                if value == "season":
                    child.pack(side="left", padx=4)
                else:
                    child.pack_forget()
        self._emit()

    # ─────────────────────────────────────────
    # 로드 / emit
    # ─────────────────────────────────────────
    def load_meta(self, meta: CharacterMeta, is_saved: bool = False):
        self._meta = meta
        self._is_saved = is_saved
        self._character_id = meta.id
        self.id_label.configure(text=str(self._character_id))

        if is_saved:
            self.regen_btn.configure(
                state="disabled",
                text="변경 불가",
                fg_color="gray30",
                hover_color="gray30",
                text_color="gray60"
            )
        else:
            self.regen_btn.configure(
                state="normal",
                text="재설정",
                fg_color=("#3B8ED0", "#1F6AA5"),
                hover_color=("#36719F", "#144870"),
                text_color="white"
            )

        self.name_var.set(meta.name)
        self.desc_entry.delete(0, "end")
        self.desc_entry.insert(0, meta.description)
        self.icon_var.set(meta.icon.strip(":"))  # ← 여기서 한 번만
        self.default_skin_var.set(meta.default_skin)

        for f, *_ in self._skin_rows:
            f.destroy()
        self._skin_rows.clear()

        for skin in meta.skins:
            self._add_skin(skin)

        # ── 이미지 폴더에 있는데 meta.skins 에 없는 스킨 자동 추가 ──
        base = self._get_image_base()
        _auto_added = False
        if base and base.exists():
            existing_names = {nv.get() for _, nv, *_ in self._skin_rows}
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name != "기본" and d.name not in existing_names:
                    self._add_skin(SkinConfig(name=d.name, skin_type="normal"))
                    _auto_added = True

        if not self._skin_rows:
            self.skin_empty_label.pack(pady=8)
        else:
            self.skin_empty_label.pack_forget()

        # 감정 목록 완전 초기화 후 새로고침
        for w in self.emotion_list_frame.winfo_children():
            w.destroy()

        if not self.get_save_path or not self.get_save_path():
            from tkinter import Label
            ctk.CTkLabel(self.emotion_list_frame,
                         text="프로젝트를 저장하면 이미지 목록이 표시됩니다.",
                         text_color="gray").pack(pady=8)
            self._update_special_emotion_menu()
            self._update_special_skin_menu()
        else:
            self._refresh_emotion_list()

        # 자동 추가된 스킨이 있으면 emit → 미저장 +1 트리거
        if _auto_added:
            self._emit()

    def _emit(self):
        try:
            # 중복 이름 제외
            seen = set()
            skins = []
            for _, nv, tv, ev, sv, ev2 in self._skin_rows:
                name = nv.get().strip()
                if name and name not in seen:
                    seen.add(name)
                    skins.append(SkinConfig(
                        name=name,
                        enabled=ev.get(),
                        skin_type=tv.get(),
                        period_start=sv.get(),
                        period_end=ev2.get()
                    ))

            meta = CharacterMeta(
                id=self._character_id,
                name=self.name_var.get(),
                description=self.desc_entry.get(),
                icon=f":{self.icon_var.get().strip()}:",  # ← 콜론 붙여서 저장
                default_skin=self.default_skin_var.get(),
                skins=skins
            )
            if self.on_change:
                self.on_change(meta)
        except Exception:
            pass