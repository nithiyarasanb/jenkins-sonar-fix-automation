import os
import subprocess
import sys
from pathlib import Path
from common import RESULTS, load_policy

def run(args):
    return subprocess.run(args, capture_output=True, text=True)

def main():
    validated = RESULTS / "validated.patch"
    if not validated.exists() or not validated.read_bytes():
        raise RuntimeError("validated.patch missing or empty")
    branch = os.environ.get("REMEDIATION_BRANCH", "")
    if not branch.startswith("sonar-remediation/") or any(x in branch for x in ("..", " ", "~", "^", ":", "?", "*", "[", "\\")):
        raise RuntimeError("Unsafe remediation branch name")
    # Reconfirm the final diff matches the validated artifact.
    current = run(["git", "diff", "--binary"])
    if current.returncode or current.stdout.encode() != validated.read_bytes():
        raise RuntimeError("Workspace diff no longer matches validated.patch")
    changed = run(["git", "diff", "--name-only"])
    if changed.returncode:
        raise RuntimeError(changed.stderr)
    policy = load_policy()
    allowed = set(policy.get("allowed_extensions", []))
    excluded = policy.get("excluded_path_prefixes", [])
    paths = [x for x in changed.stdout.splitlines() if x]
    if not paths:
        raise RuntimeError("No changed files to publish")
    if len(paths) > int(os.getenv("REMEDIATION_MAX_FILES", "5")):
        raise RuntimeError("Changed file count exceeds configured maximum")
    for path in paths:
        if Path(path).suffix not in allowed or path.startswith("/") or ".." in Path(path).parts:
            raise RuntimeError(f"Changed path is not permitted: {path}")
        if any(path.startswith(prefix) for prefix in excluded):
            raise RuntimeError(f"Excluded path changed: {path}")
    # Never commit untracked files or any files beyond the validated diff.
    branch_result = run(["git", "switch", "-c", branch])
    if branch_result.returncode:
        raise RuntimeError(branch_result.stderr)
    add = run(["git", "add", "--"] + paths)
    if add.returncode:
        raise RuntimeError(add.stderr)
    staged = run(["git", "diff", "--cached", "--name-only"])
    if staged.returncode or set(staged.stdout.splitlines()) != set(paths):
        raise RuntimeError("Staged file list differs from validated changed file list")
    commit = run(["git", "-c", "user.name=Sonar Remediation Bot", "-c",
                  "user.email=sonar-remediation-bot@users.noreply", "commit", "-m",
                  "Propose SonarQube Critical/High remediation"])
    if commit.returncode:
        raise RuntimeError(commit.stderr)
    print(f"Prepared commit on {branch}; Jenkins will push it using the restricted SSH credential.")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)
