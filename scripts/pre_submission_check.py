from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

EVIDENCE_OPTIONS: dict[str, tuple[str, ...]] = {
    "01 pytest": ("01-pytest.png", "01-pytest.txt"),
    "02 log validator": ("02-log-validator.png", "02-log-validator.txt"),
    "03 dashboard validator": ("03-dashboard-validator.png", "03-dashboard-validator.txt"),
    "04 structured log": ("04-structured-log.png",),
    "05 PII redaction": ("05-pii-redaction.png",),
    "06 trace list": ("06-trace-list.png",),
    "07 trace waterfall": ("07-trace-waterfall.png",),
    "08 trace metadata": ("08-trace-metadata.png",),
    "09 prompt versions": ("09-prompt-versions.png",),
    "10 prompt rollback": ("10-prompt-rollback.png",),
    "11 dashboard runtime": (
        "11-dashboard-overview.png",
        "11a-dashboard-latency-errors.png",
    ),
    "12 incident metric": ("12-incident-metric.png",),
    "13 incident log": ("13-incident-log.png",),
    "14 incident trace": ("14-incident-trace.png",),
}

FORBIDDEN_TRACKED = (
    ".env",
    "config/challenge.json",
    "data/logs.jsonl",
    "data/audit.jsonl",
)
FORBIDDEN_PREFIXES = (".venv/", ".pytest_cache/", "__pycache__/")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"}
SECRET_PATTERNS = (
    re.compile(r"\bsk-lf-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b", re.IGNORECASE),
)


def tracked_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def find_forbidden_tracked(paths: list[str]) -> list[str]:
    normalized = [path.replace("\\", "/") for path in paths]
    return [
        path
        for path in normalized
        if path in FORBIDDEN_TRACKED or any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
    ]


def find_secret_issues(root: Path, paths: list[str]) -> list[str]:
    issues: list[str] = []
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                issues.append(f"possible secret in {relative}")
                break
    return issues


def find_missing_evidence(root: Path) -> list[str]:
    evidence_dir = root / "submission" / "evidence"
    missing: list[str] = []
    for label, options in EVIDENCE_OPTIONS.items():
        if label.startswith("11 "):
            overview = evidence_dir / "11-dashboard-overview.png"
            split = (
                evidence_dir / "11a-dashboard-latency-errors.png",
                evidence_dir / "11b-dashboard-cost-token-quality.png",
            )
            if not overview.exists() and not all(path.exists() for path in split):
                missing.append(label)
        elif not any((evidence_dir / option).exists() for option in options):
            missing.append(label)
    return missing


def find_report_issues(root: Path) -> list[str]:
    report_path = root / "submission" / "REPORT.md"
    if not report_path.exists():
        return ["submission/REPORT.md is missing"]
    text = report_path.read_text(encoding="utf-8")
    issues: list[str] = []
    for marker in ("<MSSV>", "Chưa chụp", "Chưa thực hiện"):
        if marker in text:
            issues.append(f"report still contains placeholder: {marker}")
    if re.search(r"(?m)^- \*\*[^*]+:\*\*\s*$", text):
        issues.append("report has empty required fields")
    pending_items = [
        line
        for line in text.splitlines()
        if line.startswith("- [ ]") and "LMS/Codelabs" not in line
    ]
    if pending_items:
        issues.append("report has unchecked submission items")

    for relative in set(re.findall(r"evidence/[A-Za-z0-9_.-]+", text)):
        if not (root / "submission" / relative).exists():
            issues.append(f"report link does not exist: {relative}")
    return issues


def run_command(command: list[str], label: str) -> bool:
    print(f"\n[{label}] {' '.join(command)}")
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode == 0


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Validate the Day 13 submission before push")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Skip runtime log validation because data/logs.jsonl is intentionally not committed.",
    )
    args = parser.parse_args()

    paths = tracked_files(REPO_ROOT)
    issues = [
        *(f"forbidden tracked path: {path}" for path in find_forbidden_tracked(paths)),
        *find_secret_issues(REPO_ROOT, paths),
        *(f"missing evidence: {label}" for label in find_missing_evidence(REPO_ROOT)),
        *find_report_issues(REPO_ROOT),
    ]

    commands_ok = run_command(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        "pytest",
    )
    commands_ok &= run_command([sys.executable, "-B", "scripts/validate_dashboard.py"], "dashboard")
    if not args.ci:
        commands_ok &= run_command([sys.executable, "-B", "scripts/validate_logs.py"], "logs")

    print("\n[submission]")
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}")
    else:
        print("PASS: evidence, report, tracked files and secret scan")

    if issues or not commands_ok:
        print("\nRESULT: FAIL")
        raise SystemExit(1)
    print("\nRESULT: PASS")


if __name__ == "__main__":
    main()
