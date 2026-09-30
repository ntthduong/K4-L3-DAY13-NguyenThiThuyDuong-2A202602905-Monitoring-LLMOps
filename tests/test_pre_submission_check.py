from __future__ import annotations

from pathlib import Path

from scripts.pre_submission_check import (
    EVIDENCE_OPTIONS,
    find_forbidden_tracked,
    find_missing_evidence,
    find_report_issues,
    find_secret_issues,
)


def _complete_evidence(root: Path) -> None:
    evidence = root / "submission" / "evidence"
    evidence.mkdir(parents=True)
    for label, options in EVIDENCE_OPTIONS.items():
        if label.startswith("11 "):
            (evidence / "11-dashboard-overview.png").write_bytes(b"png")
        else:
            (evidence / options[0]).write_bytes(b"evidence")


def test_submission_checks_accept_complete_safe_fixture(tmp_path: Path) -> None:
    _complete_evidence(tmp_path)
    report = tmp_path / "submission" / "REPORT.md"
    report.write_text(
        "# Report\n- **Họ tên:** Student\n- [x] Complete\n"
        "- [ ] URL và SHA cần nộp trên LMS/Codelabs\n"
        "![Trace](evidence/07-trace-waterfall.png)\n",
        encoding="utf-8",
    )

    assert find_missing_evidence(tmp_path) == []
    assert find_report_issues(tmp_path) == []
    assert find_forbidden_tracked(["app/main.py", ".env.example"]) == []


def test_submission_checks_find_missing_and_placeholders(tmp_path: Path) -> None:
    report = tmp_path / "submission" / "REPORT.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "- **MSSV:**\n- **Project:** day13-k4-l3b-<MSSV>\n"
        "- [ ] Complete\n![Missing](evidence/14-incident-trace.png)\n",
        encoding="utf-8",
    )

    assert find_missing_evidence(tmp_path)
    issues = find_report_issues(tmp_path)
    assert any("<MSSV>" in issue for issue in issues)
    assert any("empty required fields" in issue for issue in issues)
    assert any("unchecked" in issue for issue in issues)
    assert any("does not exist" in issue for issue in issues)


def test_secret_and_forbidden_file_detection(tmp_path: Path) -> None:
    source = tmp_path / "config.py"
    fake_secret = "sk" + "-lf-" + "abcdefghijklmnop"
    source.write_text(f'token = "{fake_secret}"\n', encoding="utf-8")

    assert find_secret_issues(tmp_path, ["config.py"]) == ["possible secret in config.py"]
    assert find_forbidden_tracked([".env", "config/challenge.json", "app/main.py"]) == [
        ".env",
        "config/challenge.json",
    ]
