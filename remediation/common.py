import json
import os
from pathlib import Path

RESULTS = Path(os.getenv("REMEDIATION_RESULTS", "remediation-results"))
POLICY_PATH = Path(os.getenv("REMEDIATION_POLICY", "config/remediation-policy.json"))

def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def ensure_results():
    RESULTS.mkdir(parents=True, exist_ok=True)

def read_findings():
    p = RESULTS / "findings.json"
    if not p.exists():
        raise RuntimeError("findings.json is missing; run collect_findings.py first")
    return json.loads(p.read_text(encoding="utf-8"))

def safe_repo_path(raw_path):
    # Sonar paths are project-relative. Reject traversal and absolute paths.
    p = Path(raw_path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe repository path: {raw_path}")
    resolved = (Path.cwd() / p).resolve()
    repo = Path.cwd().resolve()
    if repo not in resolved.parents and resolved != repo:
        raise ValueError(f"Path escapes repository: {raw_path}")
    return p.as_posix()
