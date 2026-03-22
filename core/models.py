from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Step:
    delay: int = 2
    emotion: str = "기본"
    text: str = ""

    def to_dict(self) -> dict:
        return {
            "delay": self.delay,
            "emotion": self.emotion,
            "text": self.text
        }

    @staticmethod
    def from_dict(d: dict) -> "Step":
        return Step(
            delay=d.get("delay", 2),
            emotion=d.get("emotion", "기본"),
            text=d.get("text", "")
        )


@dataclass
class Button:
    id: str = ""
    skin: Optional[str] = None
    label: str = ""
    color: str = "gray"
    next: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    chance: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skin": self.skin,
            "label": self.label,
            "color": self.color,
            "next": self.next,
            "conditions": self.conditions,
            "chance": self.chance
        }

    @staticmethod
    def from_dict(d: dict) -> "Button":
        return Button(
            id=d.get("id", ""),
            skin=d.get("skin"),
            label=d.get("label", ""),
            color=d.get("color", "gray"),
            next=d.get("next", ""),
            conditions=d.get("conditions", {}),
            chance=d.get("chance")
        )


@dataclass
class Dialogue:
    id: str = ""
    skin: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    chance: Optional[int] = None
    delta: int = 0
    run: Dict[str, Any] = field(default_factory=dict)
    steps: List[Step] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skin": self.skin,
            "conditions": self.conditions,
            "chance": self.chance,
            "delta": self.delta,
            "run": self.run,
            "steps": [s.to_dict() for s in self.steps]
        }

    @staticmethod
    def from_dict(d: dict) -> "Dialogue":
        return Dialogue(
            id=d.get("id", ""),
            skin=d.get("skin"),
            conditions=d.get("conditions", {}),
            chance=d.get("chance"),
            delta=d.get("delta", 0),
            run=d.get("run", {}),
            steps=[Step.from_dict(s) for s in d.get("steps", [])]
        )


@dataclass
class Node:
    name: str = ""           # 파일명 (확장자 없음)
    dialogues: List[Dialogue] = field(default_factory=list)
    buttons: List[Button] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dialogues": [d.to_dict() for d in self.dialogues],
            "buttons": [b.to_dict() for b in self.buttons]
        }

    @staticmethod
    def from_dict(name: str, d: dict) -> "Node":
        return Node(
            name=name,
            dialogues=[Dialogue.from_dict(x) for x in d.get("dialogues", [])],
            buttons=[Button.from_dict(x) for x in d.get("buttons", [])]
        )


@dataclass
class SkinConfig:
    name: str = ""
    enabled: bool = True
    skin_type: str = "normal"   # "normal" | "season"
    period_start: str = ""      # "MM-DD"
    period_end: str = ""        # "MM-DD"

    def to_dict(self) -> dict:
        d: dict = {
            "enabled": self.enabled,
            "type": self.skin_type,
        }
        if self.skin_type == "season":
            d["period"] = {
                "start": self.period_start,
                "end": self.period_end
            }
        return d

    @staticmethod
    def from_dict(name: str, d: dict) -> "SkinConfig":
        period = d.get("period", {})
        return SkinConfig(
            name=name,
            enabled=d.get("enabled", True),
            skin_type=d.get("type", "normal"),
            period_start=period.get("start", ""),
            period_end=period.get("end", "")
        )


@dataclass
class CharacterMeta:
    id: int = 1
    name: str = ""
    description: str = ""
    icon: str = "❓"
    default_skin: str = "기본"
    skins: List[SkinConfig] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "default_skin": self.default_skin,
            "skins": {s.name: s.to_dict() for s in self.skins}
        }

    @staticmethod
    def from_dict(d: dict) -> "CharacterMeta":
        skins = [
            SkinConfig.from_dict(k, v)
            for k, v in d.get("skins", {}).items()
        ]
        return CharacterMeta(
            id=d.get("id", 1),
            name=d.get("name", ""),
            description=d.get("description", ""),
            icon=d.get("icon", "❓"),
            default_skin=d.get("default_skin", "기본"),
            skins=skins
        )


@dataclass
class Project:
    meta: CharacterMeta = field(default_factory=CharacterMeta)
    nodes: List[Node] = field(default_factory=list)
    save_path: Optional[str] = None  # 저장 폴더 경로

    def get_node(self, name: str) -> Optional[Node]:
        for n in self.nodes:
            if n.name == name:
                return n
        return None

    def node_names(self) -> List[str]:
        return [n.name for n in self.nodes]
