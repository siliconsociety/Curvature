"""Spiral grows leaves slowly and branches before directories crowd."""

from pathlib import Path

import pytest

from curvature.gate import bounds, spiral
from curvature.gate.ratchet import Ratchet


def write_lines(root: Path, relpath: str, count: int) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * count)
    return path


def configure(root: Path, *, enabled: bool = True, roots: tuple[str, ...] = ("app",)) -> None:
    rendered_roots = ", ".join(f'"{item}"' for item in roots)
    (root / "pyproject.toml").write_text(
        "[tool.curvature.spiral]\n"
        f"enabled = {str(enabled).lower()}\n"
        f"roots = [{rendered_roots}]\n"
    )


def fill_mass(root: Path, units: int, *, tree: str = "app") -> None:
    for index in range(units):
        group = index // spiral.BRANCH_LIMIT
        write_lines(root, f"{tree}/mass/group_{group}/unit_{index}.py", 300)


@pytest.mark.parametrize(
    ("mass", "expected"),
    [
        (0.9, 0),
        (1, 1),
        (2.9, 2),
        (3, 3),
        (12.9, 8),
        (13, 13),
        (20.9, 13),
        (21, 21),
        (34, 34),
        (54.9, 34),
        (55, 55),
    ],
)
def test_fibonacci_scale_is_the_greatest_crossed_threshold(mass, expected):
    assert spiral.fibonacci_scale(mass) == expected


@pytest.mark.parametrize(
    ("scale", "expected"),
    [(13, 300), (21, 381), (34, 485), (55, 617), (89, 785), (144, 998)],
)
def test_leaf_growth_is_unbounded_and_sublinear(scale, expected):
    assert round(300 * spiral.growth_for(scale)) == expected


def test_spiral_is_off_when_absent_or_disabled(tmp_path):
    assert spiral.load(tmp_path) == (None, [])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'plain'\n")
    assert spiral.load(tmp_path) == (None, [])
    configure(tmp_path, enabled=False)
    assert spiral.load(tmp_path) == (None, [])


@pytest.mark.parametrize(
    "configuration",
    [
        "[tool.curvature.spiral\n",
        "tool = 'not a table'\n",
        "[tool]\ncurvature = 'not a table'\n",
        "[tool.curvature]\nspiral = 'not a table'\n",
    ],
)
def test_malformed_spiral_tables_are_reported_or_absent(tmp_path, configuration):
    (tmp_path / "pyproject.toml").write_text(configuration)
    protocol, findings = spiral.load(tmp_path)
    assert protocol is None
    if configuration.startswith("tool ="):
        assert findings == []
    else:
        assert [finding.rule for finding in findings] == ["ANOM-152"]


def test_mass_normalizes_each_governed_language_to_its_base_ceiling(tmp_path):
    configure(tmp_path)
    write_lines(tmp_path, "app/model.py", 300)
    write_lines(tmp_path, "app/surface.css", 250)
    write_lines(tmp_path, "app/behavior.js", 150)
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert protocol.trees[0].mass == 3
    assert protocol.trees[0].scale == 3


def test_each_declared_root_has_its_own_mass(tmp_path):
    configure(tmp_path, roots=("app", "tests"))
    write_lines(tmp_path, "app/model.py", 300)
    fill_mass(tmp_path, 34, tree="tests")
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert [(tree.relpath, tree.scale) for tree in protocol.trees] == [
        ("app", 1),
        ("tests", 34),
    ]


def test_healthy_branch_receives_the_scaled_ceiling(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    target = write_lines(tmp_path, "app/feature/target.py", 485)
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert protocol.trees[0].scale == 34
    assert protocol.ceiling_for(target, Ratchet()) == 485
    assert bounds.check_ceilings(tmp_path, Ratchet(), protocol) == []


def test_overloaded_branch_keeps_the_base_ceiling(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    target = write_lines(tmp_path, "app/crowded.py", 301)
    for index in range(12):
        write_lines(tmp_path, f"app/sibling_{index}.py", 1)
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 300
    assert [finding.rule for finding in protocol.branch_findings()] == ["ANOM-152"]
    ceiling_findings = bounds.check_ceilings(tmp_path, Ratchet(), protocol)
    assert any(finding.path == "app/crowded.py" for finding in ceiling_findings)


def test_one_file_component_folder_can_use_the_tree_scale(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    target = write_lines(tmp_path, "app/components/clock/clock.py", 400)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 485


def test_grandfather_pin_is_not_multiplied(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    target = write_lines(tmp_path, "app/feature/legacy.py", 500)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    ratchet = Ratchet(exceptions={"app/feature/legacy.py": 500})
    assert protocol.ceiling_for(target, ratchet) == 500


def test_files_outside_declared_tree_keep_the_ordinary_ceiling(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    target = write_lines(tmp_path, "tests/large_test.py", 400)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 300


def test_branch_span_ignores_empty_markers_caches_and_vendor_files(tmp_path):
    configure(tmp_path)
    for index in range(13):
        write_lines(tmp_path, f"app/leaf_{index}.py", 1)
    write_lines(tmp_path, "app/__init__.py", 0)
    write_lines(tmp_path, "app/__pycache__/ghost.py", 20)
    write_lines(tmp_path, "app/static/vendor/library.js", 500)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.branch_findings() == []


def test_empty_source_tree_has_zero_mass_and_no_branches(tmp_path):
    configure(tmp_path)
    (tmp_path / "app").mkdir()
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert protocol.trees[0].mass == 0
    assert protocol.branch_findings() == []


def test_switching_spiral_off_reapplies_the_ordinary_ceiling(tmp_path):
    configure(tmp_path)
    fill_mass(tmp_path, 34)
    write_lines(tmp_path, "app/feature/large.py", 400)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert bounds.check_ceilings(tmp_path, Ratchet(), protocol) == []
    configure(tmp_path, enabled=False)
    disabled, _ = spiral.load(tmp_path)
    findings = bounds.check_ceilings(tmp_path, Ratchet(), disabled)
    assert any(finding.path == "app/feature/large.py" for finding in findings)


@pytest.mark.parametrize(
    "configuration",
    [
        "[tool.curvature.spiral]\nenabled = 'yes'\n",
        "[tool.curvature.spiral]\nroots = []\n",
        "[tool.curvature.spiral]\nroots = ['missing']\n",
        "[tool.curvature.spiral]\nroots = ['app', 'app/components']\n",
        "[tool.curvature.spiral]\nbranch_limit = 160\n",
    ],
)
def test_invalid_spiral_configuration_is_an_anomaly(tmp_path, configuration):
    write_lines(tmp_path, "app/components/clock.py", 1)
    (tmp_path / "pyproject.toml").write_text(configuration)
    protocol, findings = spiral.load(tmp_path)
    assert protocol is None
    assert [finding.rule for finding in findings] == ["ANOM-152"]


def test_roots_cannot_escape_or_repeat(tmp_path):
    (tmp_path / "app").mkdir()
    _, errors = spiral._resolve_roots(
        tmp_path,
        [str(tmp_path / "app"), "../outside", "app", "app"],
    )
    assert any("stay inside" in error for error in errors)
    assert any("repeated" in error for error in errors)
