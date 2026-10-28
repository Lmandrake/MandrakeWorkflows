import subprocess, os

# Deploy tool: copies changed mod files into the game folder and records them in git.
def record(changed_files):
    for f in changed_files:
        subprocess.run(["git", "add", f], check=True)          # stage each file
    for f in changed_files:
        subprocess.run(["git", "log", "-1", "--format=%H", f])  # last commit per file
    subprocess.run(["git", "add", "-A"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "commit", "-m", "deploy"])           # commit
    subprocess.run(["git", "status"])                           # confirm it worked

def head():
    for i in range(len(os.listdir("."))):
        subprocess.run(["git", "rev-parse", "HEAD"])            # get HEAD in a loop
