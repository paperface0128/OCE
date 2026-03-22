import customtkinter as ctk
import tkinter as tk
import json
from pathlib import Path
from core.models import Project


class FlowPage(ctk.CTkFrame):
    NODE_W = 140
    NODE_H = 54

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._project: Project | None = None
        self._positions: dict[str, tuple[int, int]] = {}
        self._drag_node: str | None = None
        self._drag_offset: tuple[int, int] = (0, 0)
        self._scale: float = 1.0

        self._select_start: tuple[float, float] | None = None
        self._select_rect_id = None
        self._selected_nodes: set[str] = set()
        self._group_drag_start: tuple[float, float] | None = None
        self._group_drag_positions: dict[str, tuple[int, int]] = {}

        self._ctrl_drag_start_y: float | None = None
        self._ctrl_drag_start_scale: float = 1.0

        self._build()

    def _build(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=36)
        toolbar.pack(fill="x", padx=8, pady=4)

        ctk.CTkButton(toolbar, text="새로고침", width=100, height=28,
                      command=lambda: self._project and self.render(self._project)
                      ).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="자동 정렬", width=100, height=28,
                      command=self._auto_layout).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="줌 초기화", width=90, height=28,
                      command=self._reset_zoom).pack(side="left", padx=4)

        self.zoom_label = ctk.CTkLabel(toolbar, text="100%", width=50)
        self.zoom_label.pack(side="left", padx=4)

        ctk.CTkLabel(toolbar,
                     text="드래그: 이동/범위 지정 | 휠: 세로 스크롤 | Shift+휠: 가로 스크롤 | Ctrl+휠: 줌",
                     text_color="gray").pack(side="left", padx=8)

        frame = ctk.CTkFrame(self, corner_radius=6)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.canvas = tk.Canvas(
            frame, bg="#1a1a2e",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # 스크롤
        self.canvas.bind("<MouseWheel>",       self._on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_wheel)

        # 마우스
        self.canvas.bind("<ButtonPress-1>",          self._on_mouse_down)
        self.canvas.bind("<B1-Motion>",               self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>",         self._on_mouse_up)

        # Ctrl 줌
        self.canvas.bind("<Control-ButtonPress-1>",   self._on_ctrl_down)
        self.canvas.bind("<Control-B1-Motion>",        self._on_ctrl_drag)
        self.canvas.bind("<Control-ButtonRelease-1>",  self._on_ctrl_up)
        self.canvas.bind("<Control-MouseWheel>",        self._on_ctrl_wheel)

    # ─────────────────────────────────────────
    # 렌더링
    # ─────────────────────────────────────────
    def render(self, project: Project):
        self._project = project
        self._load_layout()
        self._render_canvas()
    def _box_edge_point(self, nx, ny, tx, ty, s):
        """노드 박스 경계와 선의 교점 계산"""
        nw = int(self.NODE_W * s)
        nh = int(self.NODE_H * s)
        cx = int(nx * s) + nw // 2
        cy = int(ny * s) + nh // 2

        dx = tx - cx
        dy = ty - cy
        if dx == 0 and dy == 0:
            return cx, cy

        # 박스 반폭/반높
        hw = nw / 2
        hh = nh / 2

        if dx == 0:
            return cx, cy + (hh if dy > 0 else -hh)
        if dy == 0:
            return cx + (hw if dx > 0 else -hw), cy

        tx_scale = hw / abs(dx)
        ty_scale = hh / abs(dy)
        t = min(tx_scale, ty_scale)

        return int(cx + dx * t), int(cy + dy * t)
    def _render_canvas(self, skip_edges: bool = False):
        self.canvas.delete("all")
        if not self._project:
            return

        s = self._scale
        nw = int(self.NODE_W * s)
        nh = int(self.NODE_H * s)
        if not skip_edges:
            edge_pairs: dict[tuple, list] = {}
            for node in self._project.nodes:
                if node.name not in self._positions:
                    continue
                seen = set()
                for btn in node.buttons:
                    if not btn.next or btn.next not in self._positions:
                        continue
                    if (node.name, btn.next) in seen:
                        continue
                    seen.add((node.name, btn.next))
                    pair = tuple(sorted([node.name, btn.next]))
                    edge_pairs.setdefault(pair, []).append((node.name, btn.next))

            for node in self._project.nodes:
                if node.name not in self._positions:
                    continue
                sx, sy = self._positions[node.name]

                seen = set()
                for btn in node.buttons:
                    if not btn.next or btn.next not in self._positions:
                        continue
                    key = (node.name, btn.next)
                    if key in seen:
                        continue
                    seen.add(key)

                    dx, dy = self._positions[btn.next]

                    pair = tuple(sorted([node.name, btn.next]))
                    is_bidirectional = len(edge_pairs.get(pair, [])) > 1
                    is_first = not is_bidirectional or edge_pairs[pair][0] == (node.name, btn.next)

                    is_selected = (node.name in self._selected_nodes or
                                   btn.next in self._selected_nodes)
                    line_color = "#00e676" if is_selected else "#4a9eff"
                    lw = max(1, int(2 * s))

                    if is_bidirectional:
                        # 곡선 중간점 계산
                        scx = int(sx * s) + int(self.NODE_W * s) // 2
                        scy = int(sy * s) + int(self.NODE_H * s) // 2
                        dcx = int(dx * s) + int(self.NODE_W * s) // 2
                        dcy = int(dy * s) + int(self.NODE_H * s) // 2
                        offset = int(60 * s) * (1 if is_first else -1)
                        mid_x = (scx + dcx) // 2 + offset
                        mid_y = (scy + dcy) // 2

                        # 박스 경계 교점
                        x1, y1 = self._box_edge_point(sx, sy, mid_x, mid_y, s)
                        x2, y2 = self._box_edge_point(dx, dy, mid_x, mid_y, s)

                        self.canvas.create_line(
                            x1, y1, mid_x, mid_y, x2, y2,
                            smooth=True, fill=line_color, width=lw,
                            arrow="last", arrowshape=(14, 18, 6)
                        )
                        self.canvas.create_text(
                            mid_x, mid_y - int(12 * s),
                            text=btn.label or btn.next,
                            fill="#aaaaff", font=("Arial", max(7, int(8 * s)))
                        )
                    else:
                        # 꺾인 선의 중간점
                        scx = int(sx * s) + int(self.NODE_W * s) // 2
                        scy = int(sy * s) + int(self.NODE_H * s) // 2
                        dcx = int(dx * s) + int(self.NODE_W * s) // 2
                        dcy = int(dy * s) + int(self.NODE_H * s) // 2
                        mid_y = (scy + dcy) / 2

                        # 출발: 아래 또는 위 경계
                        x1, y1 = self._box_edge_point(sx, sy, scx, int(mid_y), s)
                        # 도착: 위 또는 아래 경계
                        x2, y2 = self._box_edge_point(dx, dy, dcx, int(mid_y), s)

                        self.canvas.create_line(
                            x1, y1, x1, mid_y, x2, mid_y, x2, y2,
                            smooth=True, fill=line_color, width=lw,
                            arrow="last", arrowshape=(14, 18, 6)
                        )
                        self.canvas.create_text(
                            (x1 + x2) // 2, mid_y - int(12 * s),
                            text=btn.label or btn.next,
                            fill="#aaaaff", font=("Arial", max(7, int(8 * s)))
                        )

        for node in self._project.nodes:
            if node.name not in self._positions:
                continue
            x, y = self._positions[node.name]
            rx, ry = int(x * s), int(y * s)
            is_special = node.name == "_START"  # ← _END 제거로 _START 만 특수
            fill    = "#0f3460" if not is_special else "#16213e"
            outline = "#00e676" if node.name in self._selected_nodes else (
                      "#4a9eff" if not is_special else "#e94560")
            lw = 3 if node.name in self._selected_nodes else 2

            self.canvas.create_rectangle(
                rx, ry, rx + nw, ry + nh,
                fill=fill, outline=outline, width=lw
            )
            self.canvas.create_text(
                rx + nw // 2, ry + nh // 2 - int(8 * s),
                text=node.name, fill="white",
                font=("Arial", max(8, int(10 * s)), "bold")
            )
            self.canvas.create_text(
                rx + nw // 2, ry + nh // 2 + int(10 * s),
                text=f"대사 {len(node.dialogues)}개  버튼 {len(node.buttons)}개",
                fill="#aaaaaa", font=("Arial", max(6, int(8 * s)))
            )

        bbox = self.canvas.bbox("all")
        if bbox:
            pad = 60
            self.canvas.configure(scrollregion=(
                bbox[0] - pad, bbox[1] - pad,
                bbox[2] + pad, bbox[3] + pad
            ))
        else:
            self.canvas.configure(scrollregion=(0, 0, 800, 600))

        self.zoom_label.configure(text=f"{int(self._scale * 100)}%")
    # ─────────────────────────────────────────
    # 마우스 이벤트
    # ─────────────────────────────────────────
    def _canvas_pos(self, event):
        return (self.canvas.canvasx(event.x) / self._scale,
                self.canvas.canvasy(event.y) / self._scale)

    def _hit_node(self, cx, cy) -> str | None:
        for name, (x, y) in self._positions.items():
            if x <= cx <= x + self.NODE_W and y <= cy <= y + self.NODE_H:
                return name
        return None

    def _on_mouse_down(self, event):
        cx, cy = self._canvas_pos(event)
        hit = self._hit_node(cx, cy)

        if hit:
            if hit in self._selected_nodes:
                self._group_drag_start = (cx, cy)
                self._group_drag_positions = {n: self._positions[n] for n in self._selected_nodes}
                self._drag_node = None
            else:
                self._selected_nodes.clear()
                self._drag_node = hit
                self._drag_offset = (cx - self._positions[hit][0],
                                     cy - self._positions[hit][1])
                self._group_drag_start = None
            self._select_start = None
        else:
            self._selected_nodes.clear()
            self._drag_node = None
            self._group_drag_start = None
            self._select_start = (self.canvas.canvasx(event.x),
                                  self.canvas.canvasy(event.y))

        self._render_canvas()

    def _on_mouse_drag(self, event):
        cx, cy = self._canvas_pos(event)

        if self._drag_node:
            nx = int(cx - self._drag_offset[0])
            ny = int(cy - self._drag_offset[1])
            self._positions[self._drag_node] = (nx, ny)
            self._render_canvas()
            return

        if self._group_drag_start and self._group_drag_positions:
            dx = cx - self._group_drag_start[0]
            dy = cy - self._group_drag_start[1]
            for name, (ox, oy) in self._group_drag_positions.items():
                self._positions[name] = (int(ox + dx), int(oy + dy))
            self._render_canvas()
            return

        if self._select_start:
            ex = self.canvas.canvasx(event.x)
            ey = self.canvas.canvasy(event.y)
            if self._select_rect_id:
                self.canvas.delete(self._select_rect_id)
            self._select_rect_id = self.canvas.create_rectangle(
                self._select_start[0], self._select_start[1], ex, ey,
                outline="#00e676", fill="", width=1, dash=(4, 4)
            )

    def _on_mouse_up(self, event):
        was_dragging = self._drag_node or self._group_drag_start

        if self._select_start:
            ex = self.canvas.canvasx(event.x)
            ey = self.canvas.canvasy(event.y)
            sx, sy = self._select_start

            x1 = min(sx, ex) / self._scale
            y1 = min(sy, ey) / self._scale
            x2 = max(sx, ex) / self._scale
            y2 = max(sy, ey) / self._scale

            self._selected_nodes.clear()
            for name, (nx, ny) in self._positions.items():
                nx2, ny2 = nx + self.NODE_W, ny + self.NODE_H
                if nx < x2 and nx2 > x1 and ny < y2 and ny2 > y1:
                    self._selected_nodes.add(name)

            if self._select_rect_id:
                self.canvas.delete(self._select_rect_id)
                self._select_rect_id = None
            self._select_start = None

        # 먼저 초기화 후 렌더
        self._drag_node = None
        self._group_drag_start = None
        self._group_drag_positions = {}

        # 드래그 끝나면 엣지 포함 전체 렌더 (초기화 이후에 호출)
        if was_dragging or not self._select_start:
            self._render_canvas()
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_wheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ─────────────────────────────────────────
    # Ctrl 줌
    # ─────────────────────────────────────────
    def _zoom_at(self, new_scale: float, mouse_x: float, mouse_y: float):
        old_scale = self._scale
        new_scale = max(0.3, min(3.0, new_scale))
        if new_scale == old_scale:
            return

        cx = self.canvas.canvasx(mouse_x)
        cy = self.canvas.canvasy(mouse_y)
        ratio = new_scale / old_scale
        self._scale = new_scale

        for name, (x, y) in self._positions.items():
            wx = x * old_scale
            wy = y * old_scale
            new_wx = cx + (wx - cx) * ratio
            new_wy = cy + (wy - cy) * ratio
            self._positions[name] = (
                max(10, int(new_wx / new_scale)),
                max(10, int(new_wy / new_scale))
            )

        self._render_canvas()

    def _on_ctrl_down(self, event):
        self._ctrl_drag_start_y = event.y
        self._ctrl_drag_start_scale = self._scale
        self._ctrl_mouse_x = event.x
        self._ctrl_mouse_y = event.y

    def _on_ctrl_drag(self, event):
        if self._ctrl_drag_start_y is None:
            return
        delta = self._ctrl_drag_start_y - event.y
        new_scale = self._ctrl_drag_start_scale + delta * 0.005
        self._zoom_at(new_scale, self._ctrl_mouse_x, self._ctrl_mouse_y)

    def _on_ctrl_up(self, event):
        self._ctrl_drag_start_y = None

    def _on_ctrl_wheel(self, event):
        delta = 0.1 if event.delta > 0 else -0.1
        self._zoom_at(self._scale + delta, event.x, event.y)

    def _reset_zoom(self):
        self._scale = 1.0
        self._render_canvas()

    # ─────────────────────────────────────────
    # 자동 정렬
    # ─────────────────────────────────────────
    def _auto_layout(self):
        if not self._project:
            return

        H_GAP, V_GAP = 60, 40
        visited = []
        queue = [("_START", 0)]
        col_counts: dict[int, int] = {}

        while queue:
            name, col = queue.pop(0)
            if name in visited:
                continue
            visited.append(name)
            row = col_counts.get(col, 0)
            col_counts[col] = row + 1
            self._positions[name] = (
                60 + col * (self.NODE_W + H_GAP),
                60 + row * (self.NODE_H + V_GAP)
            )
            node = self._project.get_node(name)
            if node:
                for btn in node.buttons:
                    if btn.next and btn.next not in visited:
                        queue.append((btn.next, col + 1))

        orphan_col = max(col_counts.keys(), default=0) + 2
        orphan_row = 0
        for node in self._project.nodes:
            if node.name not in self._positions:
                self._positions[node.name] = (
                    60 + orphan_col * (self.NODE_W + H_GAP),
                    60 + orphan_row * (self.NODE_H + V_GAP)
                )
                orphan_row += 1

        self._render_canvas()

    # ─────────────────────────────────────────
    # 레이아웃 저장/로드
    # ─────────────────────────────────────────
    def _layout_path(self) -> Path | None:
        if not self._project or not self._project.save_path:
            return None
        return Path(self._project.save_path) / "config" / "layout.json"

    def save_layout(self):
        path = self._layout_path()
        if not path or not self._positions:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._positions, f, ensure_ascii=False, indent=2)

    def _load_layout(self):
        path = self._layout_path()
        if path and path.exists():
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
            self._positions = {k: tuple(v) for k, v in saved.items()}
        else:
            self._positions = {}
            self._auto_layout()
            return

        if self._project:
            max_x = max((x for x, y in self._positions.values()), default=60) + self.NODE_W + 60
            row = 0
            for node in self._project.nodes:
                if node.name not in self._positions:
                    self._positions[node.name] = (max_x, 60 + row * (self.NODE_H + 40))
                    row += 1