"""The deferred audits: ANOM-150/151/161 and the audit subcommand."""

import textwrap
from pathlib import Path

from curvature.gate import checks
from curvature.gate.cli import command_audit
from curvature.gate.css import check_orphan_css


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- ANOM-150: orphan CSS ----------------------------------------------------


def test_the_lap_board_rot_would_be_caught(tmp_path):
    """The exact sediment the garden walk found by hand: selectors whose
    markup left the building."""
    write(tmp_path, "static/app.css", textwrap.dedent("""
        .lap { display: flex; }
        .lap-toggle:hover { color: red; }
        .tower { display: grid; }
    """))
    write(tmp_path, "components/view.py", 'div(class_="tower")\n')
    findings = check_orphan_css(tmp_path)
    assert sorted(f.message.split()[1] for f in findings) == [".lap", ".lap-toggle"]


def test_living_selectors_pass_including_pieced_strings(tmp_path):
    write(tmp_path, "static/app.css", textwrap.dedent("""
        .row { display: grid; }
        .row-dim { opacity: 0.7; }
    """))
    write(tmp_path, "view.py", textwrap.dedent("""
        classes = "row"
        if dim:
            classes = "row row-dim"
    """))
    assert check_orphan_css(tmp_path) == []


def test_vendored_css_is_exempt(tmp_path):
    write(tmp_path, "static/vendor/lib.css", ".third-party-thing { color: red; }\n")
    assert check_orphan_css(tmp_path) == []


def test_element_and_token_selectors_are_not_classes(tmp_path):
    write(tmp_path, "static/app.css", textwrap.dedent("""
        :root { --ink: black; }
        body { margin: 0; }
        header h1 { font-size: 2rem; }
        @media (max-width: 50rem) { body { padding: 0; } }
    """))
    assert check_orphan_css(tmp_path) == []


# --- ANOM-151: registry patterns ----------------------------------------------


def test_init_subclass_registration_is_refused(tmp_path):
    write(tmp_path, "plugin.py", textwrap.dedent("""
        class Base:
            def __init_subclass__(cls, **kwargs):
                REGISTRY.append(cls)
    """))
    findings = checks.check_registry_patterns(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-151"]


def test_metaclasses_are_refused(tmp_path):
    write(tmp_path, "magic.py", textwrap.dedent("""
        class Widget(metaclass=WidgetMeta):
            pass
    """))
    findings = checks.check_registry_patterns(tmp_path)
    assert "metaclass" in findings[0].message


def test_plain_classes_pass(tmp_path):
    write(tmp_path, "plain.py", "class Task:\n    pass\n")
    assert checks.check_registry_patterns(tmp_path) == []


# --- ANOM-161: manifest honesty --------------------------------------------------


def _satellite(tmp_path, declared, actual):
    write(tmp_path, "satellites/probe/satellite.py", textwrap.dedent(f"""
        from curvature.satellites import Satellite

        probe = Satellite(
            name="probe",
            version="0.1.0",
            components={declared!r},
        )
    """))
    for name in actual:
        write(tmp_path, f"satellites/probe/components/{name}.py", "# component\n")


def test_ghost_components_are_caught(tmp_path):
    _satellite(tmp_path, ("desk", "ghost"), ["desk"])
    findings = checks.check_manifest_honesty(tmp_path)
    assert len(findings) == 1
    assert "'ghost' that does not exist" in findings[0].message


def test_stowaway_components_are_caught(tmp_path):
    _satellite(tmp_path, ("desk",), ["desk", "stowaway"])
    findings = checks.check_manifest_honesty(tmp_path)
    assert "'stowaway' exists but the manifest" in findings[0].message


def test_honest_manifests_pass(tmp_path):
    _satellite(tmp_path, ("desk",), ["desk"])
    assert checks.check_manifest_honesty(tmp_path) == []


def test_the_poured_constellation_is_honest(tmp_path):
    from curvature.gate.scaffold import new_app, pour_satellite

    root = new_app(tmp_path, "probe_town")
    pour_satellite(root, "auth")
    pour_satellite(root, "concierge")
    assert checks.check_manifest_honesty(root) == []


# --- the audit subcommand ----------------------------------------------------------


def test_audit_walks_an_installed_package(capsys):
    # curvature itself is installed; its source honors its own contract
    assert command_audit("curvature") == 0
    assert "honors the contract" in capsys.readouterr().out


def test_audit_reports_missing_modules(capsys):
    assert command_audit("no_such_satellite_anywhere") == 1
    assert "cannot find" in capsys.readouterr().out


def test_audit_reports_a_sinful_package(tmp_path, capsys, monkeypatch):

    pkg = tmp_path / "sinful_satellite"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "hot.js").write_text('fetch("/exfil")\n')  # curvature-allow: probe
    monkeypatch.syspath_prepend(str(tmp_path))
    from curvature.gate.cli import main

    assert main(["audit", "sinful_satellite"]) == 1
    out = capsys.readouterr().out
    assert "ANOM-120" in out and "1 anomaly in sinful_satellite" not in out
    assert "anomalies in sinful_satellite" in out or "anomaly in sinful_satellite" in out


def test_single_quoted_class_strings_count_as_living(tmp_path):
    write(tmp_path, "static/app.css", ".solo { color: red; }\n.duo { color: blue; }\n")
    write(tmp_path, "view.py", "div(class_='solo')\nclasses = 'duo dim'\n")
    assert check_orphan_css(tmp_path) == []
