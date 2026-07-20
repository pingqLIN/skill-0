# Runtime Asset Security and Dependency Review

**Date:** 2026-07-18

**Updated:** 2026-07-20

**Scope:** P0 Runtime Asset Foundation and Storage Boundary

**Authority:** Local development and Runtime dry-run evidence only; this is not production security clearance.

## Decision

**LOCAL_GO / PRODUCTION_NO_GO_PENDING_BASE_CVE_FIX.** The reviewed dependency remediation is accepted for local P0/P1 development. No verified Critical or untreated High dependency finding remains in the declared Python or web dependency graphs. The Runtime Asset index is healthy after a provenance-triggered full rebuild.

The final API and Dashboard images each contain **1 Critical and 2 High** findings in Debian Bookworm's essential Perl runtime, all reported without a fixed Bookworm version. The pinned Web runtime image contains **1 Critical and 9 High** Alpine findings. These findings are treated by an explicit production deny, not by risk acceptance: none of the images is cleared for production, release, deploy, or public exposure.

## Evidence

- Initial local Python environment: 79 dependencies; 7 advisories across `pydantic-settings`, `setuptools`, `torch`, and `transformers`.
- Remediated local Python environment: 82 dependency records; 81 were auditable with no known vulnerabilities. The CPU build `torch==2.13.0+cpu` was skipped by `pip-audit` because that local-version identifier is not on PyPI; its installed version and the upstream fixed-version boundary were checked separately.
- Partial legacy `requirements.lock`: 15 pinned packages, no known vulnerabilities after remediation. The file is explicitly non-authoritative and remains incomplete.
- Web lockfile: 480 total dependencies and 0 npm audit vulnerabilities. The production web image also reported 0 vulnerabilities during `npm ci`.
- GitHub Dependabot API: 0 open alerts at capture time.
- Upgraded embedding-stack probe: all 196 Asset document vectors and five fixed query vectors were bitwise equal before and after the `transformers`/`torch` upgrade; all five top-10 ranking orders were equal.
- Strict post-upgrade indexing: first run rebuilt 196/196 because stack provenance changed; second run was 196/196 unchanged; drift doctor was `healthy` with exit code 0.
- Container builds: API, Dashboard API, and web images built successfully. The API image directly reported `sentence-transformers 5.6.0`, `transformers 5.14.1`, `torch 2.13.0+cpu`, `setuptools 83.0.0`, successful `asset_registry`/`VectorStore` imports, and a clean `pip check`.
- Container CVE scan: the former Debian Trixie API image had 1 Critical and 11 High findings. Pinning the current Bookworm image digest removed all glibc/OpenSSL findings. The final API image scan completed with exactly 1 Critical and 2 High Perl findings and no application-layer Critical/High addition.
- Follow-up offline `local://` scans on `2026-07-20` verified the pinned Dashboard candidate at 1 Critical / 2 High and the pinned Web candidate at 1 Critical / 9 High. Updating the Web base from digest `806f6d3e...` to `08c2bc9344...` reduced the observed result from 2 Critical / 14 High but did not satisfy the zero-Critical/High gate.
- All production Dockerfile stages are now digest-pinned. All remote GitHub Actions references are pinned to full commit SHAs with their intended major versions retained as comments. Static regression tests fail on a mutable Docker stage or action reference. A second isolated Compose rehearsal passed build, health, production doctor, governed dry-run, deterministic Evidence, three-store backup/restore, restart persistence, and zero-resource cleanup with the pinned images.
- Regression: 451 Python tests passed; 34 web tests passed; frontend production build and Python compile checks passed.
- Follow-up hardening regression: 505 Python/API tests and 36 frontend tests passed; frontend lint/build and schema validation 196/196 passed.

Ignored local evidence is under `.artifacts/security-review/20260717T214200Z/`, including resolver reports, audit JSON, vector comparison, and strict indexing evidence.

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

### Production blocker: Debian Perl vulnerabilities without a Bookworm fix

The completed final-image Scout report contains:

| Advisory | Severity | Trigger surface | Bookworm fixed version | Treatment |
|---|---|---|---|---|
| `CVE-2026-12087` | Critical | Perl `Socket::pack_ip_mreq_source` with a short attacker-controlled source value | Not fixed | Production deny |
| `CVE-2026-48959` | High | Perl `IO::Uncompress::Unzip` processing attacker-controlled ZIP data | Not fixed | Production deny |
| `CVE-2026-48962` | High | Perl `IO::Compress::File::GlobMapper` with an attacker-controlled output glob | Not fixed | Production deny |

The Skill-0 API runs Python as a non-root user and no inspected application path invokes Perl or exposes these Perl APIs. That lowers observed local dry-run reachability but does not erase the vulnerable essential package or authorize production use. Debian currently lists Bookworm as vulnerable for these source packages: [`CVE-2026-12087`](https://security-tracker.debian.org/tracker/CVE-2026-12087) and [`CVE-2026-48962`](https://security-tracker.debian.org/tracker/CVE-2026-48962).

Owner: Runtime maintainers. Revalidation due: **2026-07-25**. Rebuild on a fixed official base digest and run:

```powershell
docker scout cves --only-severity critical,high --format sarif --output api-cves.sarif local://skill-0-api:<review-tag>
```

Production remains blocked unless the result has zero Critical/High findings or a human explicitly approves a separate, time-bounded production exception after a fresh reachability review.

## Remaining Warnings / Blockers

1. **Dashboard/Web container CVE inventories — VERIFIED production blockers.** The Dashboard Bookworm image has the same unfixed Perl 1 Critical / 2 High set as the API. The Web image has OpenSSL 1 Critical / 8 High plus musl 1 High; Scout reports fixed boundaries `openssl>=3.5.7-r0` and `musl>=1.2.5-r23`, but the current official image digest contains older packages. The build environment's TLS trust gate prevented a safe package refresh, and no trusted-host or force-missing-repository bypass was used. Revalidate a newer official digest or an approved CA-enabled rebuild; the gate remains zero Critical/High.
2. **Incomplete legacy lock — Warning.** `requirements.lock` is not consumed by CI or containers and is not a hash-complete transitive lock. It is retained only as a labelled legacy snapshot. Replace it with per-environment, hash-verified locks or remove it through the repository's recoverable deletion workflow.
3. **Model-source boundary — Warning.** `SkillEmbedder` prefers the local cache but can fall back to remote model loading. Production should require an approved local model artifact and digest rather than accepting an arbitrary `SKILL0_EMBEDDING_MODEL` value.

Warnings and blockers are assigned to the Runtime maintainers for the first production-hardening batch. Until they are closed, this review supports local Runtime dry-runs and P1 Search evidence only.
