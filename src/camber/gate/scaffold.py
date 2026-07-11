"""camber new — the paved on-ramp.

A scaffold is steering, not convenience: the generated file already has
the Props model, the id-carrying root, and the test, so the easy next
move is to fill in the interface — not to invent a different shape.
`camber new app` extends the same idea to zero: the poured repo carries
its own gate, its own ratchet, and its own AGENTS.md, so onboarding a
human or an agent means pointing them at the directory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from camber.gate.ratchet import Ratchet, save

TEMPLATES = Path(__file__).parent / "templates"

APP_FILES = {
    "pyproject.toml.tmpl": "pyproject.toml",
    "gitignore.tmpl": ".gitignore",
    "gate.sh.tmpl": "gate.sh",
    "run.sh.tmpl": "run.sh",
    "README.md.tmpl": "README.md",
    "AGENTS.md.tmpl": "AGENTS.md",
    "main.py.tmpl": "app/main.py",
    "shell.py.tmpl": "app/components/shell.py",
    "welcome.py.tmpl": "app/components/welcome.py",
    "test_app.py.tmpl": "tests/test_app.py",
    "tarmac.css.tmpl": "app/static/tarmac.css",
}

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


def new_app(parent: Path, name: str) -> Path:
    """Pour a complete cambered app: code, tests, gate, ratchet, AGENTS.md.
    Green from birth; refuses to overwrite; git-initialized when git is
    willing (the ratchet integrity check reads git history)."""
    if not name.isidentifier() or name != name.lower():
        raise ValueError(f"{name!r} is not a valid app name (lower snake_case, please)")
    target = parent / name
    if target.exists():
        raise FileExistsError(f"{target} already exists; scaffolds never overwrite")

    title = name.replace("_", " ").title()
    for template_name, relpath in APP_FILES.items():
        text = (TEMPLATES / template_name).read_text()
        text = text.replace("__CAMBER_NAME__", name).replace("__CAMBER_TITLE__", title)
        if "__CAMBER_" in text:
            raise ValueError(f"unfilled placeholder in {template_name}")
        destination = target / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
    for script in ("gate.sh", "run.sh"):
        (target / script).chmod(0o755)
    for package in ("app", "app/components"):
        (target / package / "__init__.py").touch()
    (target / ".python-version").write_text("3.14\n")
    save(target, Ratchet())

    for command in (
        ["git", "init", "--quiet"],
        ["git", "add", "-A"],
        ["git", "commit", "--quiet", "-m", "Poured by camber new app"],
    ):
        done = subprocess.run(command, cwd=target, capture_output=True, timeout=15)
        if done.returncode != 0:
            break
    return target


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
