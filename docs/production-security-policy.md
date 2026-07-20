# Production Security Policy v1

- Status: **Accepted for the Runtime Architecture v1 stable foundation**
- Version: `1.4.0`
- Effective date: `2026-07-21`
- Machine-readable policy: [`contracts/production-security-policy-v1.json`](contracts/production-security-policy-v1.json)
- Operations: [`runtime-production-operations.md`](runtime-production-operations.md)
- Authority lifecycle: [`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- Traditional Chinese companion: [`production-security-policy.zh-tw.md`](production-security-policy.zh-tw.md)

## 1. Scope and security objective

This policy defines the minimum production controls for the stable foundation:

- single-host Docker Compose deployment;
- Core API, Governance/Dashboard API, and web services;
- `skills.db`, `governance.db`, and `runtime.db` as separate SQLite stores;
- `asset_type=skill` only; and
- dry-run-only Runtime API execution with the simulation adapter.

The objective is to preserve exact Governance authority, prevent unauthorized
Runtime decisions, contain untrusted Asset/Knowledge/Evaluation data, protect
credentials and operator stores, and retain auditable recovery evidence.

This policy does not make the current Compose file an internet edge. TLS,
firewalling, secret management, host encryption, and access logging remain
deployment controls that must be supplied outside the repository.

## 2. Evidence state

### VERIFIED application and repository controls

- Production startup rejects the development JWT secret, missing API
  credentials, localhost/wildcard CORS, Runtime binding-key placeholders or
  key reuse, missing decision actors, invalid HITL TTL, and non-WAL Runtime mode.
- API docs and OpenAPI are disabled in production configuration.
- Login and general API rate limits are configured; credential comparison uses
  fixed-length constant-time digest comparisons.
- Forwarded client-IP headers are ignored unless proxy trust is explicitly
  enabled and the peer is in configured trusted proxy CIDRs.
- Runtime create, resume, and recovery request models require
  `dry_run: Literal[True]`; the public Runtime route accepts test adapters only,
  and the simulation adapter rejects real execution.
- The Core API mounts `governance.db` read-only; the Governance service owns its
  writes. Runtime events and decision evidence use the separate Runtime store.
- Production startup and the production doctor reject
  `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`. A missing Runtime ledger must be
  restored through the verified recovery workflow; it cannot be initialized by
  a production boot.
- Public `/health` returns a liveness status only. `/api/health/detail` requires
  JWT authentication and omits database paths, storage sizes, model names, and
  version metadata.
- The Runtime doctor can require current, readable backups for all three stores
  and reports configuration names rather than secret values.
- HITL decisions require an authenticated JWT subject in
  `SKILL0_RUNTIME_DECISION_ACTORS` and expire under an immutable item deadline.
- Production requires an absolute, symlink-free, operator-materialized model
  directory plus `SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST`. Startup, model
  loading, index identity, and the production doctor compute the versioned
  complete-tree digest and fail closed on missing, malformed, unreadable, or
  mismatched artifacts. The model volume is read-only and remote model fallback
  is disabled. Errors contain stable reason codes rather than paths or digests.

### REQUIRED deployment controls not enforced by the application

- Terminate modern TLS at a maintained reverse proxy or ingress. Do not expose
  the Compose HTTP ports directly to an untrusted network.
- Restrict the Core API, metrics, health, and administrative routes with network
  ACLs. The Dashboard API should remain on an internal service network.
- Store JWT, API, and Runtime binding credentials in a secret manager or
  equivalent protected injection mechanism. Do not persist real values in a
  repository `.env` file, image layer, log, backup manifest, or shell history.
- Use unique high-entropy JWT, API password, and Runtime binding secrets. The
  application checks binding-key length and independence, but does not measure
  entropy for every credential.
- Encrypt host volumes and backups at rest, restrict file ownership/mode, and
  keep backup decryption keys separate from backup media.
- Restrict host/container administration, Docker socket access, backup paths,
  and model cache writes to named operator roles.
- Approve the exact model artifact digest before provisioning the read-only
  model volume. Host or volume administrators remain outside the application
  trust boundary even though the application verifies the mounted bytes.
- Centralize logs with retention and access controls while preserving request,
  Governance revision, Runtime run, and event correlation.
- Keep public liveness and metrics routes within the trusted network boundary;
  authentication reduces exposure but does not replace network containment.

If any required deployment control is absent, the deployment is not compliant
with this policy even if the application doctor passes.

## 3. Identity, authentication, and authorization

1. Set `SKILL0_ENV=production` and `SKILL0_ENABLE_DOCS=false`.
2. Set exact HTTPS `CORS_ORIGINS`; wildcard, localhost, and loopback origins are
   prohibited in production.
3. Replace every `CHANGE_ME` value. `JWT_SECRET_KEY` and
   `SKILL0_RUNTIME_BINDING_KEY` must be independent; the latter must contain at
   least 32 characters.
4. Configure non-empty `API_USERNAME` and `API_PASSWORD`. Transport them only
   over TLS and rotate them after suspected exposure.
5. Set `SKILL0_RUNTIME_DECISION_ACTORS` to explicit authenticated subjects. Do
   not use group-like placeholders or accept an actor supplied in a request body.
6. Keep JWT lifetime bounded. Existing tokens are invalidated through secret
   rotation; there is no separate token-revocation service in the foundation.
7. Treat Governance revision approval and Runtime HITL approval as separate
   authorities. Neither actor role implies the other.

## 4. Network and proxy boundary

- Publish only the intended web origin through the edge. Route API traffic
  through the trusted proxy; do not make the host-mapped API port generally
  reachable.
- Keep proxy-header trust disabled unless every direct peer is a controlled
  proxy and `SKILL0_TRUSTED_PROXY_CIDRS` contains only those peers.
- Restrict `/metrics`, health detail, authentication, index maintenance,
  Governance mutation, Runtime decision, and backup interfaces to the minimum
  required principals and networks.
- Do not use CORS as authentication or a network firewall.
- External tunnels, public routes, DNS, certificates, or ingress changes require
  their own explicit approval and exposure review.

## 5. Runtime and authority controls

- Production policy is dry-run-only. Any request or configuration attempting
  `dry_run=false`, a non-test public adapter, or real compensation must fail.
- Runtime admission must validate the exact current Governance revision, Asset
  identity, version, artifact digest, approver, and approval timestamp.
- Search, Knowledge Plane context, Agent Evaluation reports, Dashboard state,
  mutable `skills.status`, and prior run results are never admission authority.
- Unknown effect, risk, rule evaluator, authority, source freshness, or adapter
  outcome fails closed. Ambiguous external outcomes require reconciliation.
- Runtime HITL actor allowlists and immutable deadlines are mandatory. Approval
  records a decision; it does not automatically execute, resume, or recover.
- Current-target enforcement is implemented for approve/reject/scan/test writes
  and immutable Dashboard action-job targets. Other Governance lifecycle gaps
  remain gaps. Deployments must not claim approval expiry, quorum, dedicated
  revocation, or fresh-evidence reapproval as implemented controls.

## 6. Data, SQLite, backup, and restore

| Store | Security role | Required access |
|---|---|---|
| `skills.db` | Derived, rebuildable Index | Core API read/write; never authority |
| `governance.db` | Revision and approval authority | Governance service read/write; Core API read-only |
| `runtime.db` | Append-only event ledger and Runtime projections | Core API read/write |

- Preserve separate stores and named volumes. This policy authorizes no physical
  database migration, rename, merge, or split.
- Keep `SKILL0_RUNTIME_ALLOW_INITIALIZE=false` during normal operation. Missing
  Runtime history must fail startup rather than create an empty ledger.
- Require Runtime WAL and the configured HITL TTL. Do not globally change other
  SQLite journal/durability policies without separate evidence.
- Create an operationally matched, integrity-checked backup set containing all
  three stores. The current sequential SQLite backups are not a cross-store
  atomic snapshot; freeze relevant decisions/writers when an incident or release
  requires one logical point-in-time. Encrypt, access-control, retain, and test
  the set under operator policy.
- Rehearse restore into isolated volumes. Never overwrite the only damaged copy;
  preserve it for forensic analysis.
- Restore a matching three-store set, run the production doctor, verify identity
  and authority drift, and create a fresh governed dry run before reopening.
- Never edit append-only events, approval provenance, or historical revisions to
  conceal an incident or make restored state appear continuous.

## 7. Untrusted content, logs, and privacy

- Treat Skill payloads, Knowledge source content, benchmark inputs/candidates,
  external documents, and adapter responses as untrusted data.
- Never evaluate expressions or code from a Skill or Knowledge contract. Never
  use retrieved instructions to expand access or bypass approval.
- Enforce source classification, authorization, digest, budget, redaction, and
  prompt-injection controls before any future Knowledge resolver is enabled.
- Candidate replay provenance remains `unverified` in Agent Evaluation reports;
  do not publish private prompts, responses, or traces as benchmark evidence.
- Logs and public Evidence must omit secrets, credentials, raw authorization
  headers, private payloads, and unnecessary recovery parameters. Prefer stable
  IDs, reason codes, digests, counts, and redacted summaries.
- Public health and error responses must not expose filesystem layout, SQL text,
  stack traces, or configuration values beyond the minimum operator-safe reason
  code. The public health route returns status only; the authenticated detail
  route omits database paths, storage sizes, model names, and version metadata.

## 8. Supply chain and build policy

- Build from a reviewed commit with pinned or bounded dependency inputs. Run the
  repository dependency/security review and all release tests before promotion.
- Do not disable TLS verification or add package-manager trusted-host bypasses.
  Build CA material must use the existing ephemeral secret mount and be removed.
- Do not bake operator databases, real `.env` files, credentials, backups, or
  private benchmark artifacts into images.
- Record source commit, image digest, dependency lock digest, test results, and
  vulnerability-scan state for each release candidate.
- SBOM generation, image signing, provenance attestation, and continuous image
  scanning are recommended compensating controls but are not enforced by the
  current repository. Do not claim them without external evidence.

## 9. Production release gate

A release is blocked unless all of the following are evidenced:

1. full Python regression preserves the 459-test adoption baseline and all new
   focused tests pass;
2. frontend lint, tests, and `build:ci` pass when frontend artifacts are shipped;
3. production config fails closed for placeholder/missing credentials and unsafe
   CORS;
4. Runtime remains dry-run-only and uses only the simulation/test adapter path;
5. production doctor is healthy with initialization disabled, three valid stores,
   Runtime WAL, actor allowlist, TTL, current three-store backups, and the exact
   approved local model artifact digest;
6. restore/restart rehearsal and a fresh governed dry run pass;
7. secret/artifact diff scan finds no credential, operator DB, backup, or private
   benchmark material;
8. independent review has no unresolved Critical or Warning finding; and
9. external TLS, network ACL, secret-manager, host-volume, backup-encryption, and
   monitoring controls have operator evidence.

An unavailable check is `UNKNOWN` and blocks its claim. A timeout,
acknowledgement-only review, or passed application doctor is not evidence for an
external deployment control.

## 10. Incident response and rotation

1. Contain exposure: remove public access, disable new Runtime decisions, and
   preserve services/stores for evidence when safe.
2. Preserve correlated logs, images, configuration names, three-store backups,
   Governance audit entries, and Runtime event watermarks without copying secret
   values into the incident report.
3. Classify affected authority, Asset revisions, runs, HITL items, credentials,
   backups, and external data.
4. Rotate API/JWT/Runtime secrets through the secret manager. Binding-key
   rotation intentionally makes prior keyed execution bases and unconsumed
   Runtime resume approvals non-resumable; it does not erase Governance history.
5. Restore only from a verified matching backup set when integrity is in doubt.
6. Re-run release gates and create fresh authority/run evidence before reopening.
7. Document residual uncertainty and notify affected parties through approved
   private channels.

## 11. Prohibited production states

- real adapter or non-dry-run execution;
- wildcard/localhost production CORS or direct untrusted HTTP exposure;
- default, placeholder, shared, logged, committed, or image-baked credentials;
- empty decision-actor allowlist or unbounded/invalid HITL deadline;
- normal operation with Runtime initialization enabled;
- writable Governance mount in the Core API;
- missing/corrupt/stale three-store backup evidence;
- public metrics/admin routes without network controls;
- FTS5 production integration under this baseline;
- a new Runtime Asset type;
- Dashboard redesign as a security dependency; or
- physical database migration without a separate approved migration program.
