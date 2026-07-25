"""Spiral grows local leaves from occupied surface and bounds branches."""

from pathlib import Path

import pytest

from curvature.gate import bounds, spiral
from curvature.gate.ratchet import Ratchet


def write_lines(root: Path, relpath: str, count: int, text: str = "x = 1\n") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text * count)
    return path


def configure(
    root: Path,
    *,
    enabled: bool = True,
    roots: tuple[str, ...] | None = None,
) -> None:
    lines = ["[tool.curvature.spiral]", f"enabled = {str(enabled).lower()}"]
    if roots is not None:
        rendered = ", ".join(f'"{item}"' for item in roots)
        lines.append(f"roots = [{rendered}]")
    (root / "pyproject.toml").write_text("\n".join(lines) + "\n")


def test_spiral_is_default_on_for_a_project_and_can_be_disabled(tmp_path):
    assert spiral.load(tmp_path) == (None, [])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'plain'\n")
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert protocol.trees[0].relpath == "."

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


def test_mass_normalizes_languages_while_surface_caps_each_leaf(tmp_path):
    configure(tmp_path)
    write_lines(tmp_path, "model.py", 600)
    write_lines(tmp_path, "surface.css", 125)
    write_lines(tmp_path, "behavior.js", 75)
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    tree = protocol.trees[0]
    body = tree.bodies[tmp_path]
    assert tree.mass == 3
    assert body.mass == 3
    assert body.area == 2
    assert body.radius == pytest.approx(2 ** 0.5)


def test_one_large_file_cannot_buy_its_own_capacity(tmp_path):
    configure(tmp_path)
    target = write_lines(tmp_path, "app/large.py", 301)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 300
    assert [finding.path for finding in bounds.check_ceilings(
        tmp_path, Ratchet(), protocol
    )] == ["app/large.py"]


def test_substantial_local_leaves_create_radius_for_each_other(tmp_path):
    configure(tmp_path)
    target = write_lines(tmp_path, "app/target.py", 424)
    write_lines(tmp_path, "app/neighbor.py", 300)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 424
    assert bounds.check_ceilings(tmp_path, Ratchet(), protocol) == []


def test_tiny_split_buys_only_its_fractional_surface(tmp_path):
    configure(tmp_path)
    target = write_lines(tmp_path, "app/target.py", 315)
    write_lines(tmp_path, "app/helper.py", 30)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 315
    write_lines(tmp_path, "app/helper.py", 29)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 314


def test_descendant_mass_does_not_inflate_a_parent_leaf(tmp_path):
    configure(tmp_path)
    target = write_lines(tmp_path, "app/target.py", 301)
    for index in range(8):
        write_lines(tmp_path, f"app/components/c{index}/leaf.py", 300)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 300


def test_child_directories_form_independent_local_bodies(tmp_path):
    configure(tmp_path)
    first = write_lines(tmp_path, "app/alpha/first.py", 424)
    write_lines(tmp_path, "app/alpha/second.py", 300)
    lone = write_lines(tmp_path, "app/beta/lone.py", 301)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(first, Ratchet()) == 424
    assert protocol.ceiling_for(lone, Ratchet()) == 300


def test_each_declared_root_has_its_own_geometry(tmp_path):
    configure(tmp_path, roots=("app", "tests"))
    write_lines(tmp_path, "app/model.py", 300)
    write_lines(tmp_path, "tests/first.py", 300)
    write_lines(tmp_path, "tests/second.py", 300)
    protocol, findings = spiral.load(tmp_path)
    assert findings == []
    assert protocol is not None
    assert [(tree.relpath, tree.mass) for tree in protocol.trees] == [
        ("app", 1),
        ("tests", 2),
    ]
    assert [max(body.radius for body in tree.bodies.values()) for tree in protocol.trees] == [
        1,
        pytest.approx(2 ** 0.5),
    ]


def test_crowded_directory_keeps_base_ceilings_and_reports_branch(tmp_path):
    configure(tmp_path)
    target = write_lines(tmp_path, "app/crowded.py", 301)
    for index in range(12):
        write_lines(tmp_path, f"app/sibling_{index}.py", 300)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.ceiling_for(target, Ratchet()) == 300
    assert [finding.rule for finding in protocol.branch_findings()] == ["ANOM-152"]
    assert any(
        finding.path == "app/crowded.py"
        for finding in bounds.check_ceilings(tmp_path, Ratchet(), protocol)
    )


def test_coordination_bound_ignores_empty_cache_and_vendor_files(tmp_path):
    configure(tmp_path)
    for index in range(12):
        write_lines(tmp_path, f"app/leaf_{index}.py", 1)
    write_lines(tmp_path, "app/__init__.py", 0)
    write_lines(tmp_path, "app/__pycache__/ghost.py", 20)
    write_lines(tmp_path, "app/static/vendor/library.js", 500)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert protocol.branch_findings() == []


def test_grandfather_pin_is_exact_and_outside_roots_stays_ordinary(tmp_path):
    configure(tmp_path, roots=("app",))
    target = write_lines(tmp_path, "app/legacy.py", 500)
    write_lines(tmp_path, "app/neighbor.py", 300)
    outside = write_lines(tmp_path, "tests/large_test.py", 400)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    ratchet = Ratchet(exceptions={"app/legacy.py": 500})
    assert protocol.ceiling_for(target, ratchet) == 500
    assert protocol.ceiling_for(outside, ratchet) == 300


def test_switching_spiral_off_reapplies_the_ordinary_ceiling(tmp_path):
    configure(tmp_path)
    write_lines(tmp_path, "app/large.py", 400)
    write_lines(tmp_path, "app/neighbor.py", 300)
    protocol, _ = spiral.load(tmp_path)
    assert protocol is not None
    assert bounds.check_ceilings(tmp_path, Ratchet(), protocol) == []
    configure(tmp_path, enabled=False)
    disabled, _ = spiral.load(tmp_path)
    assert any(
        finding.path == "app/large.py"
        for finding in bounds.check_ceilings(tmp_path, Ratchet(), disabled)
    )


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
