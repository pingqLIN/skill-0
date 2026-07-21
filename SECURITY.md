# Security Policy

## Supported boundary

Security maintenance covers the Runtime Architecture v1 stable foundation on
the maintained mainline: single-host deployment, one supported Runtime Asset
type (`skill`), and dry-run-only Runtime API behavior.

Historical snapshots, unmaintained branches, modified deployments, real adapter
execution, and topologies outside the documented boundary are not covered by a
production-readiness claim.

The authoritative deployment policy is
[`docs/production-security-policy.md`](docs/production-security-policy.md). The
Traditional Chinese companion is [`SECURITY.zh-tw.md`](SECURITY.zh-tw.md).

## Reporting a vulnerability

Use the repository Security tab's private vulnerability-reporting channel when
available. If that channel is unavailable, contact the repository owner through
a private channel listed on the repository profile. Do not publish exploit
details, secrets, credentials, customer data, or a working proof of concept in a
public issue.

Include the affected commit or version, deployment boundary, reproduction
conditions, impact, and a minimal redacted proof. Maintainers will classify the
report, preserve evidence, and coordinate remediation and disclosure. Never use
a vulnerability report as authorization to access data, disrupt a deployment,
or test systems outside your own authorized environment.
