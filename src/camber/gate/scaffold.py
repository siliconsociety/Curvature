"""camber new — the paved on-ramp.

A scaffold is steering, not convenience: the generated file already has
the Props model, the id-carrying root, and the test, so the easy next
move is to fill in the interface — not to invent a different shape.
"""

from __future__ import annotations

from pathlib import Path

COMPONENT_TEMPLATE = '''\
from camber import Element, Props
from camber import html as h


class {class_name}Props(Props):
    """Declare the interface first; the component is a function of it."""


def {name}(props: {class_name}Props) -> Element:
    return h.div(
        id="{kebab}",
    )
'''

TEST_TEMPLATE = '''\
from camber import render

from {import_path} import {class_name}Props, {name}


def test_{name}_renders_its_root_id():
    markup = render({name}({class_name}Props()))
    assert 'id="{kebab}"' in markup
'''


def _class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def new_component(root: Path, dotted_path: str) -> list[Path]:
    """Create components/<name>.py and its test from a path like
    'demo/components/lap_counter'. Refuses to overwrite anything."""
    target = root / f"{dotted_path}.py"
    name = target.stem
    if not name.isidentifier():
        raise ValueError(f"{name!r} is not a valid component name (snake_case, please)")
    if "components" not in target.parent.parts:
        raise ValueError(
            f"{dotted_path!r} is not inside a components/ tree; "
            "components live where the gate can see them (C-600)"
        )
    test = root / "tests" / f"test_{name}.py"
    for path in (target, test):
        if path.exists():
            raise FileExistsError(f"{path} already exists; scaffolds never overwrite")

    substitutions = {
        "name": name,
        "class_name": _class_name(name),
        "kebab": name.replace("_", "-"),
        "import_path": str(Path(dotted_path).parent / name).replace("/", "."),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    test.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(COMPONENT_TEMPLATE.format(**substitutions))
    test.write_text(TEST_TEMPLATE.format(**substitutions))
    return [target, test]
