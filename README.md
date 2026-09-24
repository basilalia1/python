# Capstone — End-to-End Triage Script
.
> Notebook reference: `Day_3/Day-3-Activities.ipynb` §3.5 and §3.6.

Build one tool that answers the first three questions an analyst asks at a
suspect machine: **what is running**, **what changed recently**, and **what are
these files** (a SHA-256 for each, so anything can be re-checked later).

Your code goes in [`../submissions/capstone.py`](../submissions/capstone.py),
which is both importable and runnable:

```bash
python submissions/capstone.py sample_evidence
```

Graded on: correct hashes, a time window that is actually respected, a
`run_triage()` that returns its report, and a missing folder that produces a
clean error rather than a traceback. Running from a shell and this write-up are
stretch points. Check with `./grade.sh capstone`.

---

## Your write-up

Replace the placeholders below — this is §3.6. Write it so another analyst can
run your tool without you in the room.

### Purpose

This tool collects running processes, recently modified files, and SHA-256 hashes of files in a folder. It helps an analyst understand what is running, what changed recently, and identify files that can be checked again later.

### Requirements

Python 3 is required. The tool uses the Python standard library. If psutil is installed, it is used to collect running processes; otherwise, the tool falls back to the ps aux command.

### How to run

```bash
python submissions/capstone.py <folder>
```

If no folder is provided, the tool uses `sample_evidence` by default.

### Example output

```text
Processes:
1234 python
5678 code
9012 explorer.exe

Recent Files:
('notes.txt', 45)
('report.docx', 120)

Hashes:
notes.txt: 13d0f715fc93d1b3b9d94ba4a7392299fd1cfbe570119a2f5f76e6b627c7ca3b
payload.bin: 78649806a835ec7a2ee4841b75a3b90f9da7a8fd8470f3164cb885f6cc683b04
report.docx: 9b061022b2f31e808e109e1b97b592e802a5458bfbc3f50fe2412f21aa8251b0
```

### Known limitations

The tool only checks files directly inside the target folder and does not scan subfolders. Recent files are based on modification time. Process information also depends on the operating system and whether psutil is installed. With more time, I would add recursive scanning, more detailed process information, and better cross-platform process collection.
