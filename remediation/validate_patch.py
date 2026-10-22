import json
import os
import subprocess
import sys
from pathlib import Path
from common import RESULTS, ensure_results, load_policy

def run(cmd, env=None):
    print("+", cmd)
    return subprocess.run(cmd, shell=True, text=True, env=env)

def main():
    ensure_results()
    proposed = RESULTS / "proposed.patch"
    if not proposed.exists() or not proposed.read_text(encoding="utf-8").strip():
        print("No proposed patch. No PR will be created.")
        (RESULTS / "validation.json").write_text(json.dumps({"validated": False, "reason": "no patch"}), encoding="utf-8")
        return
    max_bytes = int(load_policy().get("max_patch_bytes", 50000))
    if proposed.stat().st_size > max_bytes:
        raise RuntimeError("Patch exceeds max_patch_bytes")
    # Validate patch file names and path scope before applying.
    raw = proposed.read_text(encoding="utf-8")
    for line in raw.splitlines():
        if line.startswith(("--- ", "+++ ")):
            name = line[4:].split("\t", 1)[0]
            if name in ("/dev/null", "dev/null"):
                continue
            if name.startswith("/") or ".." in Path(name).parts or not (name.startswith("a/") or name.startswith("b/")):
                raise RuntimeError(f"Unsafe patch header: {line}")
    check = subprocess.run(["git", "apply", "--check", str(proposed)], capture_output=True, text=True)
    if check.returncode:
        raise RuntimeError("Patch failed git apply --check: " + check.stderr[:1000])
    apply = subprocess.run(["git", "apply", str(proposed)], capture_output=True, text=True)
    if apply.returncode:
        raise RuntimeError("Patch application failed: " + apply.stderr[:1000])

    # Repository-specific command must come from trusted Jenkins configuration.
    command = os.getenv("VALIDATION_COMMAND", "").strip()
    if not command:
        raise RuntimeError("VALIDATION_COMMAND must be configured; refusing to mark patch validated")
    result = run(command)
    if result.returncode:
        raise RuntimeError("Validation command failed")
    # Record the exact diff to be committed, after validation.
    diff = subprocess.run(["git", "diff", "--binary"], capture_output=True)
    if diff.returncode or not diff.stdout:
        raise RuntimeError("No resulting diff after patch application")
    (RESULTS / "validated.patch").write_bytes(diff.stdout)
    (RESULTS / "validation.json").write_text(json.dumps({
        "validated": True, "validation_command": command,
        "note": "This records command exit status only; configure and run a fresh SonarQube analysis on the proposed branch before merge."
    }, indent=2), encoding="utf-8")
    print("Patch applied and validation command passed. Human PR review is still required.")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        (RESULTS / "validation.json").write_text(json.dumps({"validated": False, "error": str(e)}, indent=2), encoding="utf-8")
        sys.exit(1)
