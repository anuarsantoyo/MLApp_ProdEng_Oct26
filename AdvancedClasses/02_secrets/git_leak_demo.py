"""Class 2 helper: demonstrate that deleting a committed .env does NOT remove it
from git history. Creates a throwaway repo, runs the sequence, prints the proof."""
import os
import subprocess
import tempfile
import shutil

D = tempfile.mkdtemp(prefix="git_leak_demo_")

def git(*args):
    return subprocess.run(["git", *args], cwd=D, capture_output=True, text=True)

git("init", "-q")
git("config", "user.email", "demo@example.com")
git("config", "user.name", "demo")

# 1. accident: commit a .env that contains a key
with open(os.path.join(D, ".env"), "w") as f:
    f.write("OPENROUTER_API_KEY=sk-live-DEMO123\n")
git("add", ".env")
git("commit", "-q", "-m", "wip: config")

# 2. "fix": delete the file and ignore it, then commit the removal
os.remove(os.path.join(D, ".env"))
with open(os.path.join(D, ".gitignore"), "w") as f:
    f.write(".env\n")
git("add", ".gitignore")
git("commit", "-q", "-m", "remove .env and ignore it")

print("working files now:", sorted(x for x in os.listdir(D) if x != ".git"))
print("\ncommits that touched .env:")
print(git("log", "--all", "--oneline", "--", ".env").stdout.strip())
print("\nkey still recoverable from history:")
for line in git("log", "--all", "-p", "--", ".env").stdout.splitlines():
    if "OPENROUTER" in line:
        print("   " + line)

shutil.rmtree(D, ignore_errors=True)
