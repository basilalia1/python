# Capstone — End-to-End Triage Script

## Purpose

This tool is an end-to-end triage script designed to help an analyst answer three initial questions when investigating a potentially suspicious machine:

1. **What is running?**
2. **What changed recently?**
3. **What are these files?**

The tool collects information about running processes, recently modified files, and SHA-256 hashes for files in a specified folder. The hashes allow files to be identified and re-checked later.

## Requirements

- Python 3
- Python standard library
- `psutil` is optional

If `psutil` is installed, the tool uses it to collect running process information. If `psutil` is not available, the tool falls back to the `ps aux` command.

## How to Run

From the project directory, run:

```bash
python submissions/capstone.py sample_evidence
```

You can also specify a different folder:

```bash
python submissions/capstone.py <folder>
```

If no folder is provided, the script uses `sample_evidence` as the default folder.

## What the Tool Does

### 1. Process Collection

The script collects information about running processes.

When `psutil` is available, it collects the process ID (PID) and process name. It returns up to five processes.

If `psutil` is not installed, the script uses:

```bash
ps aux
```

and returns the first five process entries.

### 2. Recent File Detection

The script checks files directly inside the specified folder and determines how recently they were modified.

By default, the time window is:

```text
600 seconds (10 minutes)
```

Files modified within this window are reported together with their age in seconds.

### 3. SHA-256 Hashing

The script calculates a SHA-256 hash for every regular file directly inside the specified folder.

Example:

```text
notes.txt: 13d0f715fc93d1b3b9d94ba4a7392299fd1cfbe570119a2f5f76e6b627c7ca3b
```

These hashes can be used to identify files and verify whether their contents change later.

## Example Output

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

## Functions

The main functions provided by the script are:

### `check_processes()`

Collects information about currently running processes.

### `check_recent_files(folder, window_seconds=600)`

Checks files in the specified folder and returns files modified within the specified time window.

### `check_hashes(folder)`

Calculates SHA-256 hashes for files in the specified folder.

### `run_triage(folder)`

Runs all three checks and returns the complete triage report as a dictionary.

### `main(argv=None)`

Handles command-line arguments, validates the target folder, runs the triage process, and prints the results.

## Error Handling

If the specified folder does not exist, the script displays a clean error message instead of producing a traceback:

```text
Error: folder not found: <folder>
```

The script then exits with a non-zero status.

## Testing

The project includes a grading script for checking the capstone requirements.

Run:

```bash
./grade.sh capstone
```

The grading criteria include:

- Correct SHA-256 hashes
- Correct enforcement of the recent-file time window
- A working `run_triage()` function that returns its report
- Clean handling of a missing folder

## Known Limitations

- The tool only checks files directly inside the target folder.
- Subdirectories are not scanned.
- Recent files are determined using file modification time.
- Process information depends on the operating system.
- The fallback process collection uses `ps aux`, which may not be available on every operating system.
- Only a limited number of running processes are returned.

## Possible Future Improvements

With more development time, the tool could be improved by:

- Adding recursive directory scanning
- Collecting more detailed process information
- Improving cross-platform process collection
- Adding additional file metadata
- Supporting configurable output formats such as JSON
- Adding more detailed error handling

## Conclusion

This capstone provides a simple end-to-end triage tool for initial analysis of a potentially suspicious machine. It combines process enumeration, recent-file detection, and SHA-256 hashing into a single workflow, giving an analyst useful information that can be reviewed and verified later.