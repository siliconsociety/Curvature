import subprocess

from curvature.gate import markdown
from curvature.gate.cli import main
from curvature.gate.markdown import check_math


def test_markdown_math_rejects_known_github_unsafe_macro(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("$$\nvalue=\\operatorname{round}(x)\n$$\n")

    findings = check_math(tmp_path)

    assert [(finding.rule, finding.path, finding.line) for finding in findings] == [
        ("ANOM-124", "README.md", 2),
    ]
    assert "rejected by GitHub" in findings[0].message


def test_markdown_math_rejects_nonportable_inline_delimiters(tmp_path):
    document = tmp_path / "docs/GEOMETRY.md"
    document.parent.mkdir()
    document.write_text("The radius is \\(r\\).\n")

    findings = check_math(tmp_path)

    assert [(finding.rule, finding.path, finding.line) for finding in findings] == [
        ("ANOM-124", "docs/GEOMETRY.md", 1),
        ("ANOM-124", "docs/GEOMETRY.md", 1),
    ]
    assert all("backticked notation" in finding.message for finding in findings)


def test_markdown_math_accepts_portable_display_and_inline_notation(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("The radius is `r`.\n\n$$\nvalue=\\mathrm{round}(r)\n$$\n")

    assert check_math(tmp_path) == []


def test_gate_includes_markdown_math_check(tmp_path, capsys):
    document = tmp_path / "README.md"
    document.write_text("The radius is \\(r\\).\n")

    assert main(["check", str(tmp_path)]) == 1
    assert "ANOM-124 README.md:1" in capsys.readouterr().out


def test_markdown_math_skips_git_ignored_documents(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".private/\n")
    private = tmp_path / ".private/notes.md"
    private.parent.mkdir()
    private.write_text("$$\nvalue=\\operatorname{round}(x)\n$$\n")

    assert check_math(tmp_path) == []


def test_markdown_math_falls_back_when_git_is_unavailable(tmp_path, monkeypatch):
    document = tmp_path / "README.md"
    document.write_text("$$\nvalue=\\operatorname{round}(x)\n$$\n")

    def unavailable(*_args, **_kwargs):
        raise OSError("git is unavailable")

    monkeypatch.setattr(markdown.subprocess, "run", unavailable)

    assert [finding.rule for finding in check_math(tmp_path)] == ["ANOM-124"]
