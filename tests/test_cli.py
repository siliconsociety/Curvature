import json

from curvature.gate.cli import main
from curvature.gate.ratchet import Ratchet, load, previous_committed, save


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_main_check_green(tmp_path, capsys):
    write(tmp_path / "app.py", "x = 1\n")
    assert main(["check", str(tmp_path)]) == 0
    assert "the geometry holds" in capsys.readouterr().out


def test_main_check_red(tmp_path, capsys):
    write(tmp_path / "static/rogue.js", "let x = 1\n")
    assert main(["check", str(tmp_path)]) == 1
    assert "FLAT-120" in capsys.readouterr().out


def test_main_check_reports_coverage_info(tmp_path, capsys):
    write(tmp_path / "coverage.json", json.dumps({"totals": {"percent_covered": 91.3}}))
    save(tmp_path, Ratchet(coverage_floor=85.0))
    assert main(["check", str(tmp_path)]) == 0
    assert "coverage: 91.3 against a floor of 85.0" in capsys.readouterr().out


def test_main_ratchet_raises_the_floor_and_tightens_pins(tmp_path, capsys):
    write(tmp_path / "app.py", "x = 1\n")
    write(tmp_path / "legacy.py", "\n".join(["x = 1"] * 8))
    write(tmp_path / "coverage.json", json.dumps({"totals": {"percent_covered": 88.46}}))
    save(tmp_path, Ratchet(ceilings={"py": 5, "css": 250, "js": 150},
                           exceptions={"legacy.py": 20}, coverage_floor=80.0))
    assert main(["ratchet", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "tightened legacy.py: 20 -> 8" in out
    assert "coverage floor raised 80.0 -> 88.4" in out
    reloaded = load(tmp_path)
    assert reloaded.exceptions["legacy.py"] == 8
    assert reloaded.coverage_floor == 88.4


def test_main_ratchet_releases_pins_that_fit(tmp_path, capsys):
    write(tmp_path / "small.py", "x = 1\n")
    save(tmp_path, Ratchet(exceptions={"small.py": 500}))
    assert main(["ratchet", str(tmp_path)]) == 0
    assert "released small.py" in capsys.readouterr().out
    assert load(tmp_path).exceptions == {}


def test_main_ratchet_grandfather(tmp_path, capsys):
    write(tmp_path / "big.py", "\n".join(["x = 1"] * 400))
    assert main(["ratchet", str(tmp_path), "--grandfather", "big.py"]) == 0
    assert "grandfathered big.py at 400" in capsys.readouterr().out
    assert load(tmp_path).exceptions["big.py"] == 400


def test_main_ratchet_refuses_to_grandfather_nothing(tmp_path, capsys):
    assert main(["ratchet", str(tmp_path), "--grandfather", "ghost.py"]) == 1
    assert "not a source file" in capsys.readouterr().out


def test_main_new_component(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "component", "demo/components/gauge"]) == 0
    out = capsys.readouterr().out
    assert "poured demo/components/gauge.py" in out
    assert (tmp_path / "demo/components/gauge.py").exists()


def test_main_new_component_rejects_bad_paths(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "component", "demo/helpers/gauge"]) == 1
    assert "C-600" in capsys.readouterr().out


def test_previous_committed_is_none_outside_git(tmp_path):
    assert previous_committed(tmp_path) is None
