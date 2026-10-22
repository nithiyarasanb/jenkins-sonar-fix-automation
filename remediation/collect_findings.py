import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from common import RESULTS, ensure_results

def api_get(url, token):
    # SonarQube token uses HTTP Basic authentication with token as username.
    auth = base64.b64encode((token + ":").encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + auth, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def main():
    host = os.environ["SONAR_HOST_URL"].rstrip("/")
    project = os.environ["SONAR_PROJECT_KEY"]
    token = os.environ["SONAR_TOKEN"]
    severities = [s.strip().upper() for s in os.getenv("SONAR_SEVERITIES", "BLOCKER,CRITICAL").split(",") if s.strip()]
    max_issues = int(os.getenv("REMEDIATION_MAX_ISSUES", "10"))
    params = {
        "componentKeys": project,
        "resolved": "false",
        "types": "VULNERABILITY,CODE_SMELL,BUG",
        "ps": str(min(max_issues, 500)),
        "p": "1"
    }
    # SonarQube issue API versions differ. Severity filters are sent as requested.
    params["severities"] = ",".join(severities)
    data = api_get(host + "/api/issues/search?" + urllib.parse.urlencode(params), token)
    issues = data.get("issues", [])
    normalized = []
    for issue in issues[:max_issues]:
        normalized.append({
            "key": issue.get("key"),
            "rule": issue.get("rule"),
            "severity": issue.get("severity"),
            "type": issue.get("type"),
            "message": issue.get("message"),
            "component": issue.get("component"),
            "project": issue.get("project"),
            "line": issue.get("line"),
            "status": issue.get("status"),
            "cleanCodeAttribute": issue.get("cleanCodeAttribute"),
            "impacts": issue.get("impacts", [])
        })
    ensure_results()
    (RESULTS / "findings.json").write_text(json.dumps({
        "project": project, "sonar_host": host, "severities": severities,
        "total": data.get("total", len(normalized)), "issues": normalized
    }, indent=2), encoding="utf-8")
    lines = ["# SonarQube remediation report", "", f"- Project: `{project}`", f"- Requested severities: {', '.join(severities)}", f"- Findings returned: {len(normalized)}", ""]
    for i in normalized:
        lines.append(f"- **{i.get('severity')}** `{i.get('rule')}` — {i.get('message')} (`{i.get('component')}`, line {i.get('line')})")
    (RESULTS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Collected {len(normalized)} findings (server total={data.get('total', 'unknown')}).")
    if not normalized:
        print("No eligible findings returned.")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)
