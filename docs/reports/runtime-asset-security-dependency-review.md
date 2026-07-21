# Runtime Asset Security and Dependency Review

**Date:** 2026-07-18

**Updated:** 2026-07-21

**Scope:** P0 Runtime Asset Foundation and Storage Boundary

**Authority:** Local development and Runtime dry-run evidence only; this is not production security clearance.

## Decision

**LOCAL_GO / REPOSITORY_SECURITY_GATE_GO / PRODUCTION_NO_GO_PENDING_EXTERNAL_OPERATOR_EVIDENCE.** The reviewed dependency and image remediation is accepted for the repository-controlled Runtime foundation. The final API, Dashboard, and Web images each report zero Critical and zero High findings. The Runtime Asset index remains healthy and the API base migration preserves the checked embedding vectors bit for bit.

The API now uses a same-release Ubuntu 24.04 multi-stage image because the PyTorch CPU wheels require a glibc-compatible runtime. Its all-severity inventory contains 15 Medium and 5 Low Ubuntu findings, retained below as residual risk; none is Critical or High under the scanner/vendor classification. Dashboard moved independently to Python Alpine 3.24 and reports zero findings at every severity after upgrading the image's build/runtime `pip`. Web remains zero at every severity. Production, deploy, and public exposure are still blocked because real signed operator evidence for the required external controls has not been supplied or verified.

## Evidence

- Initial local Python environment: 79 dependencies; 7 advisories across `pydantic-settings`, `setuptools`, `torch`, and `transformers`.
- Remediated local Python environment: 82 dependency records; 81 were auditable with no known vulnerabilities. The CPU build `torch==2.13.0+cpu` was skipped by `pip-audit` because that local-version identifier is not on PyPI; its installed version and the upstream fixed-version boundary were checked separately.
- Removed legacy `requirements.lock`: its 15-package partial snapshot was never consumed by CI or containers and could be mistaken for an authoritative lock. The recoverable local copy is retained under ignored `.del/`; active environment inputs remain the scoped `requirements-*.txt` files until a separately reviewed hash-complete lock workflow is adopted.
- Web lockfile: 480 total dependencies and 0 npm audit vulnerabilities. The production web image also reported 0 vulnerabilities during `npm ci`.
- GitHub Dependabot API: 0 open alerts at capture time.
- Upgraded embedding-stack probe: all 196 Asset document vectors and five fixed query vectors were bitwise equal before and after the `transformers`/`torch` upgrade; all five top-10 ranking orders were equal.
- Strict post-upgrade indexing: first run rebuilt 196/196 because stack provenance changed; second run was 196/196 unchanged; drift doctor was `healthy` with exit code 0.
- Container builds: API, Dashboard API, and web images built successfully. The API image directly reported `sentence-transformers 5.6.0`, `transformers 5.14.1`, `torch 2.13.0+cpu`, `setuptools 83.0.0`, successful `asset_registry`/`VectorStore` imports, and a clean `pip check`.
- Container CVE scan: the former Debian Trixie API image had 1 Critical and 11 High findings. Pinning the current Bookworm image digest removed all glibc/OpenSSL findings. The final API image scan completed with exactly 1 Critical and 2 High Perl findings and no application-layer Critical/High addition.
- Follow-up offline `local://` scans on `2026-07-20` verified the pinned Dashboard candidate at 1 Critical / 2 High and the pinned Web candidate at 1 Critical / 9 High. Updating the Web base from digest `806f6d3e...` to `08c2bc9344...` reduced the observed result from 2 Critical / 14 High but did not satisfy the zero-Critical/High gate.
- A fresh `2026-07-21` rebuild and `local://` scan reproduced API at 1 Critical / 2 High, Dashboard at 1 Critical / 2 High, and Web at 1 Critical / 9 High. The same rehearsal verified the new approved local model artifact digest gate; see [`runtime-production-compose-rehearsal-2026-07-21.md`](runtime-production-compose-rehearsal-2026-07-21.md).
- A later `2026-07-21` Web-only remediation replaced the runtime base with the official multi-architecture digest `sha256:90d82b3358df5758b3c57d20f2565082ce6f744906e7dc09afd0096c1b8eb2b5`. The rebuilt final Web image (`sha256:f604964103605aae8e96fafd642a0bc3a937596638252bd9291aa9f74aec29fc`) was scanned with Docker Scout as `0 Critical / 0 High / 0 Medium / 0 Low`; the SARIF contains zero results and has SHA-256 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`. An isolated bridge-network smoke returned HTTP 200 while the container ran as user `101`.
- Final API remediation uses digest-pinned `ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90` in a same-release multi-stage build. Image `sha256:dc7ac417bcfb3ebf49eefaffb3b1834bfd34a5b4e3e0984b4f06d5af4111c088` passed imports, `pip check`, HTTP 200, UID 65532, build-CA absence, and a 10-vector bitwise comparison against the prior Bookworm control. Its Critical/High SARIF has zero results and SHA-256 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`; its all-severity SARIF has 15 Medium and 5 Low results and SHA-256 `bdf53c8f2785d151e3bebcd7c1c95e01e87257e2a3d8d5642cf946f2e3999330`.
- Final Dashboard remediation uses digest-pinned `python:3.12-alpine3.24@sha256:f7fd610959cae736251523b54eb26cecb74f60ffa60bf39d9faccf128b526ab8` and bounded `pip>=26.1.2,<27`. Image `sha256:be736191417bcbed79406dde15aa70b585aff2d17daf82d0473232bcaa666bd3` passed imports, `pip check`, HTTP 200, and non-root user checks. Its all-severity SARIF contains zero results and has SHA-256 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`.
- A fail-closed Ed25519 external-control verifier now validates schema, a protected-runner keyring SHA-256 trust anchor, key revocation, actor role/environment authorization, freshness and expiry, exact Git/tree/keyring/Compose/policy/model/image binding, the complete eight-control policy set, path-contained attachments, and attachment digests. It rejects tracked or untracked non-ignored source drift. Missing, stale, malformed, tampered, wrong-scope, unauthorized, or incomplete evidence returns `UNKNOWN` and exit code 2. The verifier proves integrity and scope, not physical control truth; real bundles and keyrings remain external and uncommitted.
- All production Dockerfile stages are now digest-pinned. All remote GitHub Actions references are pinned to full commit SHAs with their intended major versions retained as comments. Static regression tests fail on a mutable Docker stage or action reference. A second isolated Compose rehearsal passed build, health, production doctor, governed dry-run, deterministic Evidence, three-store backup/restore, restart persistence, and zero-resource cleanup with the pinned images.
- Regression: 451 Python tests passed; 34 web tests passed; frontend production build and Python compile checks passed.
- Follow-up hardening regression: 508 Python/API tests and 36 frontend tests passed; frontend lint/build and schema validation 196/196 passed.
- Final Item 3 regression: 555 Python/API tests passed; frontend lint, 36 tests, production build, and bundle-size gate passed; schema validation remained 196/196. A fresh isolated Compose rehearsal passed all prior gates and confirmed zero residual containers, volumes, or networks.
- Independent read-only review initially returned `NO_GO` with two Warning findings: caller-selectable keyring trust and an untracked-source blind spot. The protected-runner keyring digest anchor, signed keyring binding, all-untracked Git check, and regression tests closed both findings. The second review returned `GO` for repository-controlled Item 3 with no Critical or Warning; production remained independently `NO_GO` without real external evidence.

Ignored local evidence is under `.artifacts/security-review/20260717T214200Z/` and `.artifacts/security-review/20260721-item3-final/`, including resolver reports, audit JSON, vector comparison, strict indexing evidence, and final-image SARIF. These files are local evidence, not publishable release artifacts.

## Findings and Treatment

### Resolved High: vulnerable Transformers 4.x boundary

The prior `transformers<5` constraint resolved to 4.57.6 and was affected by multiple unsafe model/config deserialization paths, including advisories fixed at 5.0, 5.3, and 5.5. The declared boundary is now `transformers>=5.14.1,<6`, paired with `sentence-transformers>=5.6,<6` and `torch>=2.13,<3`.

The major-version change was not accepted on resolver evidence alone. A local, offline `all-MiniLM-L6-v2` comparison proved bitwise-identical vectors and stable rankings for the checked corpus and queries. This is bounded compatibility evidence, not a claim that every model supported by Transformers is equivalent.

Primary references: [GHSA-fgcw-684q-jj6r](https://github.com/advisories/GHSA-fgcw-684q-jj6r), [GHSA-69w3-r845-3855](https://github.com/advisories/GHSA-69w3-r845-3855), [GHSA-29pf-2h5f-8g72](https://github.com/advisories/GHSA-29pf-2h5f-8g72), and [CVE-2025-14929](https://nvd.nist.gov/vuln/detail/CVE-2025-14929).

### Resolved High: embedding stack drift was absent from index identity

The incremental index previously identified only the model artifact/version. A dependency upgrade could therefore reuse old vectors without proving compatibility. Index identity now incorporates a SHA-256 digest of the installed `sentence-transformers`, `transformers`, and `torch` versions. The added test proves that stack-version drift forces re-embedding while an unchanged stack remains a no-op.

### Resolved: packaging and settings advisories

- `torch` was raised from 2.12.1 to 2.13.0; the prior advisory's fixed boundary is 2.13.0.
- `setuptools` was raised from 81.0.0 to 83.0.0. The API Dockerfile no longer downgrades it after application dependency installation.
- `pydantic-settings` was raised from 2.14.1 to 2.14.2.
- `PyJWT` and `pytest` minimums, plus the legacy snapshot pins, were raised to currently audited boundaries.

Primary references: [PyTorch advisory](https://github.com/advisories/GHSA-rrmf-rvhw-rf47), [pydantic-settings advisory](https://github.com/advisories/GHSA-4xgf-cpjx-pc3j), and [PyPA pip-audit](https://pypi.org/project/pip-audit/).

### Resolved: API container omitted Runtime Asset code

The dependency-reviewed API image initially failed while importing `VectorStore` because `asset_registry/` was not copied into the image. The Dockerfile now includes that package, and the final image import probe passes.

### Resolved production blocker: Bookworm Critical/High Perl findings

The historical Bookworm final-image Scout report contained:

| Advisory | Severity | Trigger surface | Bookworm fixed version | Treatment |
|---|---|---|---|---|
| `CVE-2026-12087` | Critical | Perl `Socket::pack_ip_mreq_source` with a short attacker-controlled source value | Not fixed | Production deny |
| `CVE-2026-48959` | High | Perl `IO::Uncompress::Unzip` processing attacker-controlled ZIP data | Not fixed | Production deny |
| `CVE-2026-48962` | High | Perl `IO::Compress::File::GlobMapper` with an attacker-controlled output glob | Not fixed | Production deny |

The API moved to the reviewed, digest-pinned Ubuntu 24.04 same-release multi-stage design; Dashboard moved independently to Python Alpine 3.24. The final scanned images have zero Critical and zero High findings, so the former Bookworm deny is closed without cross-release package surgery, finding suppression, TLS bypass, or a vulnerability exception. The API still contains Ubuntu `perl-base` and other OS packages with 15 Medium and 5 Low findings; their presence and vendor severity are recorded rather than described as absent.

The maintained revalidation command is:

```powershell
docker scout cves --only-severity critical,high --format sarif --output api-cves.sarif local://skill-0-api:<review-tag>
```

The zero-Critical/High result is now satisfied. Any future image change must rerun this command and invalidates the present image-bound evidence.

## Remaining Warnings / Blockers

1. **API lower-severity inventory — VERIFIED residual risk, not a Critical/High exception.** The Ubuntu API image has 15 Medium and 5 Low results across 13 OS packages. The findings remain in the retained all-severity SARIF and must be reassessed on every base/package refresh. Their vendor severity does not authorize suppressing them or describing the image as vulnerability-free.
2. **External-control operator evidence — UNKNOWN and release-blocking.** The repository now has a signed, exact-release-bound verifier, but no real bundle, external trusted keyring, attachment set, or physical observation was supplied. TLS termination, network ACL, secret management, unique credential quality, volume protection, encrypted separated backups, host/container administration, and centralized log controls therefore remain `UNKNOWN`. A synthetic fixture or successful application doctor cannot close this gate.
3. **Model approval boundary — application control resolved; deployment evidence still required.** Production requires an absolute, symlink-free local model directory and an operator-approved complete-tree digest. Startup, `SkillEmbedder`, index identity, and the production doctor fail closed when the artifact is missing, malformed, unreadable, or mismatched; remote fallback remains available only outside production and the Compose model volume is read-only. The real deployment bundle must bind the reviewed model digest because host and volume administration remain outside the application trust boundary.
4. **Source-to-image and SARIF target binding — Advisory.** The release verifier rejects tracked and untracked non-ignored source drift, while the runbook requires a dedicated release checkout. The retained SARIF does not independently encode the scanned local image ID. Under policy v1.6.0, OCI provenance, image signing, a digest-stamped scan envelope, and continuous scanning remain recommended rather than enforced. Promote this Advisory into a required control before claiming cryptographic source-to-image provenance.

The repository-controlled security work is ready for the RC branch. Production remains `NO_GO` until an authorized operator supplies a fresh signed evidence bundle for the exact clean commit, policy, Compose file, deployed image digests, model digest, and named environment, and the verifier returns `VERIFIED`. No deploy, public exposure, real credential use, or exception was performed here.
