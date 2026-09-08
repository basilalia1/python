import sys,shutil
print("python version:", sys.version)
print("git available:", shutil.which("git") is not None)
