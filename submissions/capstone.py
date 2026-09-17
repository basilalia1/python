"""Capstone -- end-to-end triage tool.

This is the one deliverable that is a real script as well as a module: the
grader imports the functions AND runs the file from a shell, so keep the
`if __name__ == "__main__"` block at the bottom intact.

    python submissions/capstone.py sample_evidence

From notebook section 3.5. Check your work with:  ./grade.sh capstone
"""

import hashlib
import os
import subprocess
import sys
import time


def check_processes():
   
    try:
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            processes.append(f"{proc.info['pid']} {proc.info['name']}")
            if len(processes) >= 5:
                break
        return processes

    except ImportError:
     result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    lines = result.stdout.splitlines()
    return lines[1:6]
def check_recent_files(folder, window_seconds=600):
    recent = []

    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)

        if os.path.isfile(path):
            age = int(time.time() - os.path.getmtime(path))

            if age <= window_seconds:
                recent.append((filename, age))

    return recent

def check_hashes(folder):
    hashes = {}
    for filename in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, filename)):
            with open(os.path.join(folder, filename), "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            hashes[filename] = file_hash
    return hashes


def run_triage(folder):
    report = {
        "folder": folder,
        "processes": check_processes(),
        "recent_files": check_recent_files(folder),
        "hashes": check_hashes(folder),
    }
    return report

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    folder = argv[0] if argv else "sample_evidence"

    if not os.path.isdir(folder):
        print(f"Error: folder not found: {folder}")
        return 1

    report = run_triage(folder)

    print("Processes:")
    for proc in report["processes"]:
        print(proc)

    print("\nRecent Files:")
    for f in report["recent_files"]:
        print(f)

    print("\nHashes:")
    for filename, file_hash in report["hashes"].items():
        print(f"{filename}: {file_hash}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

    #.