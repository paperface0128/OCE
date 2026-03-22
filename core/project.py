import json
from pathlib import Path
from .models import Project, CharacterMeta, Node


def new_project() -> Project:
    import random
    from .models import Dialogue, Step

    new_id = random.randint(10**19, 10**20 - 1)

    start_node = Node(
        name="_START",
        dialogues=[
            Dialogue(
                id="intro_first",
                steps=[Step(delay=2, emotion="기본", text="안녕하세요!")]
            )
        ],
        buttons=[]
    )

    return Project(
        meta=CharacterMeta(id=new_id, name=""),
        nodes=[start_node]
    )


def load_project(folder: str) -> Project:
    base = Path(folder)

    meta_path = base / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.json이 없습니다: {meta_path}")

    with open(meta_path, encoding="utf-8") as f:
        meta = CharacterMeta.from_dict(json.load(f))

    scripts_path = base / "scripts"
    all_nodes: dict[str, Node] = {}

    if scripts_path.exists():
        for p in scripts_path.glob("*.json"):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            all_nodes[p.stem] = Node.from_dict(p.stem, data)

    # node_order.json 으로 순서 복원
    order_path = base / "node_order.json"
    if order_path.exists():
        with open(order_path, encoding="utf-8") as f:
            order = json.load(f)
        nodes = [all_nodes[n] for n in order if n in all_nodes]
        # 순서에 없는 노드 뒤에 추가
        for name, node in all_nodes.items():
            if name not in order:
                nodes.append(node)
        # node_order.json 삭제 (더 이상 불필요)
        order_path.unlink(missing_ok=True)
    else:
        # 순서 파일 없으면 _START 최상단, 나머지 그대로
        start = [n for n in all_nodes.values() if n.name == "_START"]
        middle = [n for n in all_nodes.values() if n.name != "_START"]
        nodes = start + middle

    if "_START" not in [n.name for n in nodes]:
        nodes.insert(0, Node(name="_START"))

    return Project(meta=meta, nodes=nodes, save_path=folder)


def save_project(project: Project, folder: str):
    base = Path(folder)
    base.mkdir(parents=True, exist_ok=True)

    scripts_path = base / "scripts"
    scripts_path.mkdir(exist_ok=True)

    with open(base / "meta.json", "w", encoding="utf-8") as f:
        json.dump(project.meta.to_dict(), f, ensure_ascii=False, indent=2)

    existing = {p.stem for p in scripts_path.glob("*.json")}
    current = {n.name for n in project.nodes}

    for removed in existing - current:
        (scripts_path / f"{removed}.json").unlink(missing_ok=True)

    # _START 항상 첫 번째로 정렬
    ordered = sorted(project.nodes, key=lambda n: (0 if n.name == "_START" else 1))

    for node in ordered:
        with open(scripts_path / f"{node.name}.json", "w", encoding="utf-8") as f:
            json.dump(node.to_dict(), f, ensure_ascii=False, indent=2)

    project.save_path = folder