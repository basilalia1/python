"""Capstone -- the end-to-end triage tool.

Graded against `submissions/capstone.py` and `Capstone/README.md`. This suite
both imports the module and runs the file as a real command, because the
 .deliverable is a script someone else has to be able to run.
"""

import hashlib
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.day("capstone")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "submissions", "capstone.py")
README = os.path.join(REPO_ROOT, "Capstone", "README.md")

PLACEHOLDERS = [
    "_What does your tool collect, and what question does it answer?_",
    "_Python version, and any package a user has to install first._",
    "_paste a real run here_",
    "_What does it miss? What would you add with another day?_",
]


# --------------------------------------------------------------------------
# Required
# --------------------------------------------------------------------------

@pytest.mark.floor
@pytest.mark.points(10)
def test_check_hashes(capstone, evidence_dir):
    """check_hashes() maps every filename to its digest"""
    hashes = capstone.check_hashes(evidence_dir)

    assert isinstance(hashes, dict), f"expected a dict, got {type(hashes).__name__}"
    assert set(hashes) == {"old_report.docx", "notes.txt", "payload.bin"}
    with open(os.path.join(evidence_dir, "notes.txt"), "rb") as handle:
        assert hashes["notes.txt"] == hashlib.sha256(handle.read()).hexdigest()


@pytest.mark.floor
@pytest.mark.points(10)
def test_check_recent_files(capstone, evidence_dir):
    """check_recent_files() honours the time window"""
    recent = dict(capstone.check_recent_files(evidence_dir, 600))
    assert set(recent) == {"payload.bin"}, f"expected only payload.bin, got {sorted(recent)}"

    wider = dict(capstone.check_recent_files(evidence_dir, 7200))
    assert set(wider) == {"payload.bin", "notes.txt"}, f"expected two files, got {sorted(wider)}"


@pytest.mark.floor
@pytest.mark.points(10)
def test_run_triage_returns_report(capstone, evidence_dir):
    """run_triage() returns the combined report as a dict"""
    report = capstone.run_triage(evidence_dir)

    assert isinstance(report, dict), (
        f"run_triage() must return the report dict, not just print it -- got "
        f"{type(report).__name__}"
    )
    assert set(report) == {"folder", "processes", "recent_files", "hashes"}, (
        f"expected keys folder/processes/recent_files/hashes, got {sorted(report)}"
    )
    assert set(report["hashes"]) == {"old_report.docx", "notes.txt", "payload.bin"}
    assert dict(report["recent_files"]) == dict(capstone.check_recent_files(evidence_dir))
    assert report["processes"], "the process check came back empty"


@pytest.mark.floor
@pytest.mark.points(10)
def test_missing_folder_is_handled(capstone, capsys, tmp_path):
    """A missing folder produces a clean error, not a traceback"""
    missing = str(tmp_path / "no_such_folder")

    try:
        status = capstone.main([missing])
    except Exception as exc:  # noqa: BLE001 -- that is exactly what we are testing for
        pytest.fail(
            f"main() raised {type(exc).__name__} on a missing folder. Check the path with "
            "os.path.isdir() and print an error instead of crashing.",
            pytrace=False,
        )

    assert status != 0, "main() should return a non-zero status when the folder is missing"
    captured = capsys.readouterr()
    output = (captured.out + captured.err).lower()
    assert output.strip(), "print a message saying what went wrong"


# --------------------------------------------------------------------------
# Stretch
# --------------------------------------------------------------------------

@pytest.mark.ceiling
@pytest.mark.points(5)
def test_check_processes(capstone):
    """check_processes() returns a short sample of running processes"""
    processes = capstone.check_processes()

    assert isinstance(processes, list), f"expected a list, got {type(processes).__name__}"
    assert 0 < len(processes) <= 5, f"expected between 1 and 5 entries, got {len(processes)}"


@pytest.mark.ceiling
@pytest.mark.points(5)
def test_runs_as_a_command(evidence_dir):
    """The script runs from a shell and prints a usable report"""
    result = subprocess.run(
        [sys.executable, SCRIPT, evidence_dir],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"`python submissions/capstone.py <folder>` exited {result.returncode}:\n"
        f"{result.stderr[-800:]}"
    )
    assert "payload.bin" in result.stdout, (
        "the printed report should name the files it examined -- stdout was:\n"
        f"{result.stdout[:500]}"
    )


@pytest.mark.ceiling
@pytest.mark.points(5)
def test_readme_is_written(capstone):
    """Capstone/README.md has been filled in"""
    assert os.path.exists(README), "Capstone/README.md is missing"
    text = open(README).read()

    left = [p for p in PLACEHOLDERS if p in text]
    assert not left, (
        f"{len(left)} placeholder(s) still in Capstone/README.md -- replace them with your "
        f"own write-up. First one: {left[0]}"
    )
    for heading in ("Purpose", "Requirements", "How to run", "Example output", "Known limitations"):
        assert heading in text, f"the README is missing its '{heading}' section"
