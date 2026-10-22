# Jenkins + SonarQube Critical/High Remediation

A starter implementation for collecting SonarQube findings, generating a minimal patch using deterministic rules or an optional OpenAI-compatible AI endpoint, validating the patch, and opening a Bitbucket Pull Request.

## Safety model

- Does **not** merge Pull Requests or deploy applications.
- Never writes to the source branch. Jenkins uses a dedicated remediation branch.
- Only applies unified diffs that pass `git apply --check` and repository-scope checks.
- Fails closed on unsupported severity mappings, malformed patches, or validation failures.
- AI output is untrusted. Never put secrets in prompts; use a restricted endpoint and credentials.
- Developer approval and Bitbucket branch restrictions must be configured in Bitbucket. Jenkins does not override them.

## Prerequisites

- Jenkins agent with Python 3.10+, Git, and the build/test tools used by your repository.
- Existing SonarQube project and Jenkins SonarQube installation.
- Bitbucket repository write permission for a dedicated bot account/app password or access token.
- SonarQube token with permission to browse the target project.
- Optional: an OpenAI-compatible AI service. Configure its URL/model and store its API key in Jenkins Credentials.
- Existing language-specific build/test commands. Do not assume one command works for every repository.

## Configure Jenkins credentials

Create these credentials in Jenkins (Secret text unless noted):
- `sonarqube-token` — SonarQube user token.
- `bitbucket-token` — Bitbucket API token with PR creation permissions.
- `bitbucket-ssh-key` — Jenkins SSH Username with private key credential, write access only to the target repository.
- `remediation-ai-token` — optional AI endpoint key.

Configure Jenkins environment variables or job parameters:
- `SONAR_HOST_URL`, `SONAR_PROJECT_KEY`
- `BITBUCKET_BASE_URL` — Cloud: `https://api.bitbucket.org/2.0`; Data Center: your REST API base, e.g. `https://bitbucket.example/rest/api/1.0`
- `BITBUCKET_WORKSPACE`, `BITBUCKET_REPO_SLUG` (Cloud)
- For Data Center, set `BITBUCKET_PROJECT_KEY` and `BITBUCKET_REPO_SLUG`
- `BITBUCKET_DEFAULT_BRANCH`
- `REMEDIATION_MODE=hybrid` (`deterministic`, `ai`, or `hybrid`)
- Optional AI: `AI_BASE_URL`, `AI_MODEL`
- `REMEDIATION_MAX_ISSUES=10`, `REMEDIATION_MAX_FILES=5`

## SonarQube severity mapping

SonarQube APIs differ by version. The collector accepts `SONAR_SEVERITIES`, defaulting to `BLOCKER,CRITICAL`. Set this to the values supported by your instance. Some versions expose `HIGH` directly; older issue APIs commonly use `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`, `INFO`. Do not blindly map `MAJOR` to High: confirm your SonarQube version and quality profile.

The collector requests unresolved issues for the configured project and writes:
- `remediation-results/findings.json`
- `remediation-results/report.md`

## Running locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SONAR_HOST_URL=https://sonar.example
export SONAR_PROJECT_KEY=my-project
export SONAR_TOKEN='...'
python remediation/collect_findings.py
python remediation/propose_fixes.py
python remediation/validate_patch.py
```

The default policy intentionally has no generic source rewrite rules. Add deterministic fixes only for exact, well-tested rule patterns. Without a configured AI endpoint or deterministic rule, an issue is reported as `manual_review`.

## Jenkins integration

Use the supplied `Jenkinsfile` as a template, or move stages into your existing Jenkinsfile. Keep your existing checkout, build, test, SonarQube analysis and quality-gate stages. This example assumes the SonarQube scan has already run and that `SONAR_PROJECT_KEY` points to that analysis.

The validation command is deliberately supplied as `VALIDATION_COMMAND` rather than assuming a language:
- Java/Maven: `./mvnw -B verify`
- Java/Gradle: `./gradlew test`
- Python: `python -m pytest`
- Node.js: `npm ci && npm test`

Only use commands appropriate for the checked-out repository. For monorepos, configure a trusted wrapper script that tests the affected component(s).

## AI adapter contract

The optional adapter sends a limited source excerpt and Sonar issue description to an OpenAI-compatible `/chat/completions` endpoint and expects a unified diff. It does not send repository credentials, environment variables, or files outside the finding context. Review your organization's data-processing policy before enabling an external model.

## Bitbucket support

This starter includes Bitbucket Cloud PR creation. For Bitbucket Data Center, implement the corresponding REST API adapter for your installed version and test it against a non-production repository before enabling it. The script intentionally refuses to create a PR if required Cloud configuration is missing. Branch publication uses a separate restricted SSH credential.

## Production hardening checklist

1. Use a dedicated, isolated Jenkins agent/container with no production credentials.
2. Pin tool versions and restrict network egress.
3. Enforce Bitbucket branch restrictions, required reviewers, and passing build checks.
4. Restrict the bot token to one repository where possible; rotate it.
5. Require a human reviewer who is not the bot.
6. Add allowlists for eligible Sonar rule keys and file extensions.
7. Run secret scanning and dependency/security checks on the proposed branch.
8. Keep generated patches and prompts only as long as policy allows; redact sensitive source context.
9. Add rate limits, duplicate-PR detection, and concurrency locks per repository.
10. Never grant the AI agent shell access, Git credentials, or direct deployment credentials.
