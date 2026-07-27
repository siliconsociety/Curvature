"""The Event Horizon fence: consumer authority is declared, narrow, and measured."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curvature.gate import checks, event_horizons


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def declaration(
    name: str = "editor",
    *,
    network: bool = False,
    capabilities: dict[str, bool] | None = None,
    stylesheet: bool = False,
    javascript_budget: int = 1000,
) -> dict:
    declared_capabilities = {
        "network": network,
        "storage": False,
        "html_injection": False,
    }
    declared_capabilities.update(capabilities or {})
    value = {
        "spec": "curvature-event-horizon/0.2",
        "name": name,
        "purpose": "Keep local drafting inside one identified form",
        "entrypoint": f"{name}.js",
        "server_contract": {
            "source_of_truth": "native form fields",
            "submission": "native HTML form",
        },
        "capabilities": declared_capabilities,
        "budget_bytes": {"javascript": javascript_budget},
    }
    if stylesheet:
        value["stylesheet"] = f"{name}.css"
        value["budget_bytes"]["css"] = 500
    return value


def horizon(
    root: Path,
    script: str = "// local drafting\n",
    *,
    name: str = "editor",
    manifest: dict | None = None,
) -> Path:
    directory = f"app/static/vendor/{name}"
    write(root, f"{directory}/{name}.js", script)
    value = manifest if manifest is not None else declaration(name)
    write(root, f"{directory}/event-horizon.json", json.dumps(value))
    if value.get("stylesheet"):
        write(root, f"{directory}/{value['stylesheet']}", ".editor { color: red; }\n")
    return root / directory


def messages(findings) -> list[str]:
    return [finding.message for finding in findings]


def test_a_valid_network_free_horizon_is_chartered(tmp_path):
    horizon(tmp_path)
    assert checks.check_js_placement(tmp_path) == []
    assert checks.check_js_http(tmp_path) == []
    assert checks.check_js_capabilities(tmp_path) == []


def test_v02_network_true_means_fetch_only(tmp_path):
    horizon(
        tmp_path,
        "\n".join((
            'fetch("/allowed")',
            'new XMLHttpRequest()',
            'new WebSocket("/socket")',
            'new EventSource("/events")',
            'navigator.sendBeacon("/audit")',
        )),
        manifest=declaration(network=True),
    )
    findings = checks.check_js_http(tmp_path)
    assert [finding.message.split()[0] for finding in findings] == [
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
    ]


def test_network_false_rejects_fetch(tmp_path):
    horizon(tmp_path, 'globalThis.fetch ("/forbidden")\n')
    findings = checks.check_js_http(tmp_path)
    assert [finding.rule for finding in findings] == ["ANOM-121"]
    assert "fetch exceeds" in findings[0].message


def test_only_the_exact_declared_entrypoint_is_chartered(tmp_path):
    directory = horizon(tmp_path)
    write(tmp_path, "app/static/vendor/editor/extra.js", "// stowaway\n")
    findings = checks.check_js_placement(tmp_path)
    assert [finding.path for finding in findings] == [
        "app/static/vendor/editor/extra.js"
    ]
    assert "'entrypoint' declares 'editor.js'" in findings[0].message
    assert directory.is_dir()


def test_vendor_javascript_without_a_manifest_stays_unchartered(tmp_path):
    write(tmp_path, "app/static/vendor/editor/editor.js", "// invisible fence\n")
    findings = checks.check_js_placement(tmp_path)
    assert [finding.rule for finding in findings] == ["ANOM-120"]
    assert "no valid sibling event-horizon.json" in findings[0].message


def test_only_the_exact_consumer_path_can_declare_a_horizon(tmp_path):
    write(tmp_path, "static/vendor/editor/editor.js", "// old blanket escape\n")
    write(
        tmp_path,
        "static/vendor/editor/event-horizon.json",
        json.dumps(declaration()),
    )
    findings = checks.check_js_placement(tmp_path)
    assert len(findings) == 1
    assert "unchartered JavaScript" in findings[0].message


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"spec": "curvature-event-horizon/0.3"}, "field 'spec'"),
        ({"name": "other"}, "field 'name'"),
        ({"purpose": ""}, "field 'purpose'"),
        ({"server_contract": {}}, "field 'server_contract'"),
        ({"entrypoint": "../escape.js"}, "field 'entrypoint'"),
        ({"mystery": True}, "unknown field 'mystery'"),
    ],
)
def test_invalid_manifest_fields_fail_predictably(tmp_path, change, expected):
    value = declaration()
    value.update(change)
    horizon(tmp_path, manifest=value)
    findings = checks.check_js_placement(tmp_path)
    assert expected in messages(findings)[0]
    assert "no valid sibling event-horizon.json" in messages(findings)[-1]


def test_malformed_json_is_a_manifest_and_entrypoint_anomaly(tmp_path):
    directory = horizon(tmp_path)
    (directory / "event-horizon.json").write_text("{")
    findings = checks.check_js_placement(tmp_path)
    assert len(findings) == 2
    assert "cannot read valid JSON" in findings[0].message
    assert "no valid sibling event-horizon.json" in findings[1].message


def test_manifest_root_must_be_an_object(tmp_path):
    directory = horizon(tmp_path)
    (directory / "event-horizon.json").write_text("[]")
    findings = checks.check_js_placement(tmp_path)
    assert "manifest root must be an object" in findings[0].message


def test_manifest_cannot_be_a_symlink(tmp_path):
    directory = horizon(tmp_path)
    outside = write(tmp_path, "outside.json", json.dumps(declaration()))
    (directory / "event-horizon.json").unlink()
    (directory / "event-horizon.json").symlink_to(outside)
    findings = checks.check_js_placement(tmp_path)
    assert "must be a regular file" in findings[0].message


def test_horizon_directories_cannot_be_symlinked_into_the_vendor_root(tmp_path):
    outside = tmp_path / "outside-editor"
    horizon(tmp_path, name="outside-editor")
    source = tmp_path / "app/static/vendor/outside-editor"
    outside.parent.mkdir(parents=True, exist_ok=True)
    source.rename(outside)
    source.symlink_to(outside, target_is_directory=True)
    findings = checks.check_js_placement(tmp_path)
    assert "must be a regular file inside the declared horizon" in findings[0].message


def test_vendor_root_cannot_be_a_symlink(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-vendor"
    horizon(tmp_path)
    vendor = tmp_path / "app/static/vendor"
    vendor.rename(outside)
    vendor.symlink_to(outside, target_is_directory=True)
    findings = checks.check_js_placement(tmp_path)
    assert [finding.path for finding in findings] == ["app/static/vendor"]
    assert "must be a real directory inside app/static" in findings[0].message


def test_missing_declared_files_are_named(tmp_path):
    value = declaration()
    value["entrypoint"] = "ghost.js"
    horizon(tmp_path, manifest=value)
    findings = checks.check_js_placement(tmp_path)
    assert "declares missing file 'ghost.js'" in findings[0].message


def test_declared_entrypoint_symlink_cannot_escape_the_horizon(tmp_path):
    directory = horizon(tmp_path)
    outside = write(tmp_path, "outside.js", "// outside authority\n")
    (directory / "editor.js").unlink()
    (directory / "editor.js").symlink_to(outside)
    findings = checks.check_js_placement(tmp_path)
    assert "must name one .js file inside its horizon" in findings[0].message


def test_a_symlink_alias_does_not_gain_the_entrypoints_charter(tmp_path):
    directory = horizon(tmp_path)
    (directory / "alias.js").symlink_to(directory / "editor.js")
    findings = checks.check_js_placement(tmp_path)
    assert [finding.path for finding in findings] == [
        "app/static/vendor/editor/alias.js"
    ]
    assert "'entrypoint' declares 'editor.js'" in findings[0].message


def test_required_top_level_and_filename_fields_are_named(tmp_path):
    value = declaration()
    value.pop("purpose")
    value["entrypoint"] = None
    horizon(tmp_path, manifest=value)
    text = "\n".join(messages(checks.check_js_placement(tmp_path)))
    assert "required field 'purpose' is missing" in text
    assert "field 'entrypoint' must be a filename" in text


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda value: value["capabilities"].update({"network": "yes"}),
            "capabilities.network",
        ),
        (
            lambda value: value["capabilities"].update({"camera": True}),
            "unknown capability 'camera'",
        ),
        (
            lambda value: value["capabilities"].pop("storage"),
            "capabilities.storage",
        ),
        (
            lambda value: value["budget_bytes"].update({"javascript": 0}),
            "budget_bytes.javascript",
        ),
    ],
)
def test_authority_and_budget_schema_cannot_be_invented(tmp_path, mutate, expected):
    value = declaration()
    mutate(value)
    horizon(tmp_path, manifest=value)
    findings = checks.check_js_placement(tmp_path)
    assert expected in messages(findings)[0]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("capabilities", [], "field 'capabilities' must be an object"),
        ("budget_bytes", [], "field 'budget_bytes' must be an object"),
        ("budget_bytes", {}, "required field 'budget_bytes.javascript' is missing"),
        (
            "budget_bytes",
            {"javascript": 100, "css": 100},
            "field 'budget_bytes.css' has no declared artifact",
        ),
    ],
)
def test_nested_manifest_objects_are_exact(tmp_path, field, value, expected):
    manifest = declaration()
    manifest[field] = value
    horizon(tmp_path, manifest=manifest)
    assert expected in "\n".join(messages(checks.check_js_placement(tmp_path)))


def test_declared_javascript_and_css_byte_budgets_are_enforced(tmp_path):
    value = declaration(stylesheet=True, javascript_budget=2)
    directory = horizon(tmp_path, "four\n", manifest=value)
    (directory / "editor.css").write_text("x" * 501)
    findings = checks.check_js_placement(tmp_path)
    assert [finding.path for finding in findings] == [
        "app/static/vendor/editor/editor.js",
        "app/static/vendor/editor/editor.css",
    ]
    assert all("observed" in finding.message for finding in findings)


def test_false_machine_visible_capabilities_are_enforced(tmp_path):
    horizon(
        tmp_path,
        "\n".join((
            'localStorage.setItem("draft", "yes")',
            'target.innerHTML = "<b>unsafe</b>"',
            'history.pushState({}, "", "/next")',
            "new Intl.DateTimeFormat()",
        )),
    )
    findings = checks.check_js_capabilities(tmp_path)
    assert [finding.rule for finding in findings] == ["ANOM-123"] * 4
    assert [finding.message.split(".")[1].split()[0] for finding in findings] == [
        "storage",
        "html_injection",
        "history",
        "local_time",
    ]


def test_declared_non_network_capabilities_pass(tmp_path):
    horizon(
        tmp_path,
        "\n".join((
            'localStorage.setItem("draft", "yes")',
            'target.innerHTML = "<b>trusted</b>"',
            'history.replaceState({}, "", "/next")',
            "new Intl.DateTimeFormat()",
        )),
        manifest=declaration(
            capabilities={
                "storage": True,
                "html_injection": True,
                "history": True,
                "local_time": True,
            },
        ),
    )
    assert checks.check_js_capabilities(tmp_path) == []


def test_capability_probe_honors_a_reasoned_escape_hatch(tmp_path):
    horizon(
        tmp_path,
        'localStorage.clear() // curvature-allow: test probe\n',
    )
    assert checks.check_js_capabilities(tmp_path) == []


def test_catalog_exposes_only_a_structurally_valid_charter(tmp_path):
    directory = horizon(tmp_path)
    catalog = event_horizons.load(tmp_path)
    assert catalog.findings == ()
    assert catalog.entrypoint_for(directory / "editor.js") is not None
    assert catalog.entrypoint_for(directory / "not-editor.js") is None
