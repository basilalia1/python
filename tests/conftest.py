"""Fixtures for the autograder.
#.

Two things matter here:

1. Student modules are imported lazily inside a fixture. A broken submission
   then shows up as a failing test with a readable message instead of wiping
   out collection for the whole day.
2. Every fixture builds its own data in a temp directory, using values that
   deliberately differ from the notebook samples. Answers have to be computed,
   not remembered.
"""

import importlib
import json
import os
import re
import socket
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# Student modules
# --------------------------------------------------------------------------

def _submission(name):
    try:
        return importlib.import_module(f"submissions.{name}")
    except SyntaxError as exc:
        pytest.fail(f"submissions/{name}.py has a syntax error on line {exc.lineno}: "
                    f"{exc.msg}", pytrace=False)
    except ImportError as exc:
        pytest.fail(f"could not import submissions/{name}.py: {exc}", pytrace=False)


@pytest.fixture(scope="module")
def day1():
    return _submission("day1")


@pytest.fixture(scope="module")
def day2():
    return _submission("day2")


@pytest.fixture(scope="module")
def day3():
    return _submission("day3")


@pytest.fixture(scope="module")
def capstone():
    return _submission("capstone")


# --------------------------------------------------------------------------
# Notebook inspection
# --------------------------------------------------------------------------

def _attempted(source):
    """True when a student added real code after the `# Exercise N:` marker.

    Blank lines, comments and the placeholder `pass` do not count.
    """
    lines = source.splitlines()
    marker = max((i for i, line in enumerate(lines)
                  if line.strip().startswith("# Exercise")), default=None)
    if marker is None:
        return False
    for line in lines[marker + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.split("#")[0].strip() in ("", "pass"):
            continue
        return True
    return False


@pytest.fixture
def notebook():
    """Return a loader giving [(exercise_number, attempted), ...] for a day.

    Exercise cells are found by their `# Exercise N:` marker rather than by
    position, so reordering or adding cells does not break the check.
    """
    def load(day):
        path = os.path.join(REPO_ROOT, f"Day_{day}", f"Day-{day}-Activities.ipynb")
        with open(path) as handle:
            cells = json.load(handle).get("cells", [])
        sources = ["".join(cell.get("source", [])) for cell in cells
                   if cell.get("cell_type") == "code"]
        return [(n, _attempted(src)) for n, src in
                enumerate((s for s in sources
                           if any(l.strip().startswith("# Exercise") for l in s.splitlines())), 1)]
    return load


# --------------------------------------------------------------------------
# Day 1 -- log text
# --------------------------------------------------------------------------

AUTH_LOG = """\
Feb 11 22:01:03 srv sshd: Accepted password for dana from 10.10.0.2
Feb 11 22:01:41 srv sshd: Failed password for root from 203.0.113.77
Feb 11 22:01:44 srv sshd: Failed password for root from 203.0.113.77
Feb 11 22:02:02 srv sshd: Failed password for admin from 198.51.100.5
Feb 11 22:02:30 srv sshd: Failed password for root from 203.0.113.77
Feb 11 22:03:11 srv sshd: Accepted password for erin from 10.10.0.3
Feb 11 22:03:59 srv sshd: Failed password for git from 192.0.2.44
Feb 11 22:04:20 srv sshd: Failed password for admin from 198.51.100.5
"""

# Deliberately includes a DEBUG level the notebook never mentions, and one line
# carrying two IP addresses, so re.search() alone is not enough.
LEVEL_LOG = """\
2026-04-01 10:00:00 INFO Service started
2026-04-01 10:00:31 DEBUG Cache warm on host 10.5.0.1
2026-04-01 10:01:12 ERROR Connection refused from 203.0.113.9
2026-04-01 10:01:13 ERROR Connection refused from 203.0.113.9
2026-04-01 10:02:40 WARNING Disk usage at 91% on host 10.5.0.1
2026-04-01 10:03:05 INFO Health check OK
2026-04-01 10:04:19 ERROR Timeout talking to 198.51.100.23 via 10.5.0.1
"""


@pytest.fixture
def auth_log(tmp_path):
    path = tmp_path / "grader_auth.log"
    path.write_text(AUTH_LOG)
    return str(path)


@pytest.fixture
def level_log(tmp_path):
    path = tmp_path / "grader_levels.log"
    path.write_text(LEVEL_LOG)
    return str(path)


# --------------------------------------------------------------------------
# Day 2 -- traffic CSV, files, sockets, faked HTTP
# --------------------------------------------------------------------------

# Note 10.3.0.5 has the most connections (5) but 10.3.0.4 moves the most bytes.
TRAFFIC_CSV = """\
timestamp,src_ip,dst_port,protocol,bytes
2026-04-01T11:00:00,10.3.0.4,443,tcp,1500
2026-04-01T11:00:03,10.3.0.5,80,tcp,900
2026-04-01T11:00:07,10.3.0.4,443,tcp,2500
2026-04-01T11:00:11,10.3.0.9,31337,tcp,40
2026-04-01T11:00:19,10.3.0.5,53,udp,110
2026-04-01T11:00:24,10.3.0.4,443,tcp,700
2026-04-01T11:00:31,10.3.0.9,31337,tcp,55
2026-04-01T11:00:38,10.3.0.5,80,tcp,1200
2026-04-01T11:00:45,10.3.0.4,443,tcp,300
2026-04-01T11:00:52,10.3.0.5,80,tcp,600
2026-04-01T11:01:00,10.3.0.7,22,tcp,250
2026-04-01T11:01:05,10.3.0.5,22,tcp,80
"""


@pytest.fixture
def traffic_csv(tmp_path):
    path = tmp_path / "grader_traffic.csv"
    path.write_text(TRAFFIC_CSV)
    return str(path)


@pytest.fixture
def hashable_file(tmp_path):
    path = tmp_path / "evidence.bin"
    path.write_bytes(b"triage sample payload\n\x00\x01\x02binary tail")
    return str(path)


class FakeResponse:
    """Stand-in for a `requests` response, so grading needs no internet."""

    def __init__(self, status_code, text, payload=None):
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": "application/json"}
        self._payload = payload
        self.json_called = False

    def json(self):
        self.json_called = True
        if self._payload is None:
            raise ValueError("response body is not JSON")
        return self._payload


class HttpLog(list):
    """Every faked response, plus the canned values the tests assert against."""

    body = "".join(str(i % 10) for i in range(250))
    uuid = "8f14e45f-ceea-467a-9f1e-7c2b6d3a55e1"


@pytest.fixture
def http(monkeypatch, day2):
    """Swap requests.get for a router that answers without touching the network."""
    sent = HttpLog()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/uuid"):
            response = FakeResponse(200, '{"uuid": "%s"}' % sent.uuid, {"uuid": sent.uuid})
        else:
            match = re.search(r"/status/(\d+)", url)
            response = FakeResponse(int(match.group(1)) if match else 200, sent.body)
        sent.append((url, response))
        return response

    monkeypatch.setattr(day2.requests, "get", fake_get)
    if hasattr(day2, "get"):  # student wrote `from requests import get`
        monkeypatch.setattr(day2, "get", fake_get)
    return sent


@pytest.fixture
def open_port():
    """A TCP port on 127.0.0.1 that is genuinely accepting connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(5)
    yield server.getsockname()[1]
    server.close()


@pytest.fixture
def closed_port():
    """A port that was bound and released, so nothing is listening on it."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


# --------------------------------------------------------------------------
# Day 3 -- evidence folders and artifact exports
# --------------------------------------------------------------------------

EVIDENCE_FILES = [
    # (filename, contents, age in seconds)
    ("old_report.docx", "R" * 400, 86400),
    ("notes.txt", "N" * 120, 3600),
    ("payload.bin", "P" * 40, 30),
]


@pytest.fixture
def evidence_dir(tmp_path):
    folder = tmp_path / "grader_evidence"
    folder.mkdir()
    now = time.time()
    for name, contents, age in EVIDENCE_FILES:
        path = folder / name
        path.write_text(contents)
        os.utime(path, (now - age, now - age))
    return str(folder)


ARTIFACTS_CSV = """\
timestamp,event_type,path
2026-04-01T08:00:01,process_started,/usr/bin/bash
2026-04-01T08:12:15,file_created,/tmp/loader.sh
2026-04-01T08:44:20,process_started,/tmp/loader.sh
2026-04-01T09:05:44,file_created,/tmp/beacon.bin
2026-04-01T09:30:10,file_created,/tmp/loader.sh
2026-04-01T10:02:10,file_deleted,/tmp/loader.sh
"""


@pytest.fixture
def artifacts_csv(tmp_path):
    path = tmp_path / "grader_artifacts.csv"
    path.write_text(ARTIFACTS_CSV)
    return str(path)


@pytest.fixture
def dup_dir(tmp_path):
    folder = tmp_path / "grader_dupes"
    folder.mkdir()
    (folder / "invoice.docx").write_text("identical payload content\n")
    (folder / "svchost.exe").write_text("identical payload content\n")
    (folder / "backup.tmp").write_text("identical payload content\n")
    (folder / "notes.txt").write_text("unrelated content\n")
    (folder / "readme.md").write_text("also unrelated\n")
    return str(folder)
