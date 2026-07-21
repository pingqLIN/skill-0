# Runtime Production Compose Rehearsal Evidence — 2026-07-21

- Date: `2026-07-21`
- Status: **TECHNICAL_REHEARSAL_PASS / PRODUCTION_NO_GO**
- Authority: English version; see the Traditional Chinese companion for reference
- Candidate branch: `codex/skill0-runtime-asset-rc`

## Scope

This report records a local, isolated rerun of the production Compose contract
after adding the approved embedding-model artifact digest gate. It validates
repository-controlled model provisioning, startup, storage, health, governed
dry-run, backup/restore, restart, and cleanup behavior. It is not a deployment,
public-exposure approval, vulnerability exception, or operator production
decision.

The rerun used loopback ports `28082` and `23082`, synthetic rehearsal-only
credentials and origins, a unique Compose project, and disposable named
volumes. It did not read a real production environment file or create a public
route.

## Model artifact gate

The application code now requires an absolute, symlink-free local model directory
and `SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST`. The digest is a versioned,
length-framed SHA-256 manifest over every regular file path, size, and content
digest. Production startup, model loading, index identity, and the production
doctor fail closed when the artifact is absent, malformed, unreadable, or
mismatched. Remote model fallback is disabled and the normal API service mounts
the model volume read-only. Symlinks are forbidden at the configured directory
and within its artifact tree; ancestors outside that tree remain part of the
operator-managed host and volume boundary.

The live Compose rehearsal deliberately uses a small synthetic artifact. It
proves digest calculation, startup enforcement, read-only mounting, doctor
verification, and restart stability; it does **not** claim that the synthetic
bytes are a usable SentenceTransformer model or that real model inference ran.
Focused tests separately verify that `SkillEmbedder` checks the digest before
importing/loading the model and preserves non-production remote fallback.

The first rerun attempt safely failed because the non-root API image could not
seed a newly created model volume. The rehearsal was corrected so only the
one-shot operator provisioning container uses root; the normal API container
remains non-root with a read-only mount. The failed project cleaned up its
disposable volume before the verified rerun.

## Verified rerun

The passing rerun used:

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0modelgate0721c `
  -ApiPort 28082 `
  -WebPort 23082
```

| Gate | Evidence |
|---|---|
| Compose build and startup | API, Dashboard, and Web images built; services reached their expected health states |
| Model artifact | Disposable artifact digest was computed before startup; production doctor reported `embedding_model_artifact.verified=true` before and after restart |
| Production doctor | `healthy`; all three SQLite stores passed `quick_check`; Runtime used WAL; parsed corpus count was `196` |
| Governed Runtime | Synthetic current revision approved; dry-run status `succeeded` |
| Evidence projection | Deterministic public Evidence was generated without exposing rehearsal credentials |
| Persistence | Runtime sentinel remained present after API restart |
| Backup/restore | Online backup and restore of Index, Governance, and Runtime stores each returned `quick_check=ok`; restored Runtime sentinel matched |
| Cleanup | The project containers, volumes, and network were removed after the run |

Repository verification reported:

- model/production focused regression: `53 passed`;
- full Python/API regression: `518 passed, 76 warnings`;
- schema validation: `196 passed, 0 failed`;
- Python compile and `git diff --check`: passed.

## Fresh image scan

Docker Scout `local://` SARIF scans from the preceding passing
`skill0modelgate0721b` rerun reported:

| Image | Critical | High | SARIF SHA-256 |
|---|---:|---:|---|
| API | 1 | 2 | `feeea495903b630cc2e9029927bd80a531cbb91367b60891c4fee85548c9cb84` |
| Dashboard | 1 | 2 | `feeea495903b630cc2e9029927bd80a531cbb91367b60891c4fee85548c9cb84` |
| Web | 1 | 9 | `81d072bb8b6fe1f2de7831f4a5a24e9aa59435d63fdfc7d5448a8e418ae5fb3b` |

The outer parallel scan command reached its five-minute timeout, but all three
SARIF files were complete, valid JSON, and independently parsed after the
command ended. The counts match the prior scans. Integrity-checked copies are
retained under the ignored local evidence directory
`.artifacts/security-review/20260721T023719Z/`; they are not release artifacts.
The final `skill0modelgate0721c` rerun removed only the two image-level offline
environment defaults; Docker inspection confirmed that the API candidates have
identical 20-layer RootFS lists. Production Compose still sets both offline
flags, and no package filesystem layer changed after the retained scan.

## Remaining production boundary

The repository-controlled model artifact gap is closed, but production remains
`NO_GO`:

- at rehearsal time, all three images violated the zero-Critical/High gate;
- external TLS, network ACL, secret-manager, host-volume, encrypted-backup, and
  monitoring evidence remains outside the repository; and
- no deploy, public exposure, production secret use, or vulnerability exception
  was performed or authorized.

The explicit exclusions remain unchanged: no FTS5 production integration,
Dashboard redesign, new Asset Type, physical database migration, or real
adapter.

## Post-rehearsal Web image remediation

Later on `2026-07-21`, the Web-only runtime base was refreshed to the official
digest-pinned `nginxinc/nginx-unprivileged:1.31.3-alpine3.24-slim` image. The
rebuilt final Web image passed an isolated HTTP 200 smoke as non-root user `101`.
Docker Scout reported `0 Critical / 0 High / 0 Medium / 0 Low`; the zero-result
SARIF has SHA-256
`69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`.

This closed the Web image CVE blocker at that point. The original table above
remains historical scan evidence; the current Item 3 image and rehearsal gate is
superseded by the final rerun below.

## Final Item 3 image remediation and rerun

The API moved from Python Bookworm to a digest-pinned, same-release Ubuntu 24.04
multi-stage image. The final runtime uses the distro Python 3.12 interpreter,
copies a builder-created virtual environment, runs as UID 65532, and retains the
ephemeral BuildKit CA secret boundary. PyTorch CPU has no musllinux wheel, so the
API did not move to Alpine. The Dashboard image moved independently to
digest-pinned Python Alpine 3.24 and bounded `pip>=26.1.2,<27`.

Final local image evidence:

| Image | Local image ID | Critical | High | Medium | Low |
|---|---|---:|---:|---:|---:|
| API | `sha256:dc7ac417bcfb3ebf49eefaffb3b1834bfd34a5b4e3e0984b4f06d5af4111c088` | 0 | 0 | 15 | 5 |
| Dashboard | `sha256:be736191417bcbed79406dde15aa70b585aff2d17daf82d0473232bcaa666bd3` | 0 | 0 | 0 | 0 |
| Web | `sha256:f604964103605aae8e96fafd642a0bc3a937596638252bd9291aa9f74aec29fc` | 0 | 0 | 0 | 0 |

The zero-result Critical/High SARIF for every image has SHA-256
`69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`.
The API all-severity SARIF has SHA-256
`bdf53c8f2785d151e3bebcd7c1c95e01e87257e2a3d8d5642cf946f2e3999330`.
All API residuals are Ubuntu vendor-classified Medium or Low; they remain
visible residual risk and are not described as absent. Dashboard and Web are
zero at every severity.

The final API and the prior Bookworm control resolved identical versions of
NumPy, PyTorch, SentenceTransformers, and Transformers. Five fixed queries and
five parsed documents produced ten normalized 384-dimensional vectors with
identical per-vector SHA-256 values. API and Dashboard standalone smokes both
returned HTTP 200 as non-root users, and both images passed `pip check`.

The fresh isolated rehearsal used:

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0-item3-gate-0721b `
  -ApiPort 18184 `
  -WebPort 13184 `
  -BuildCaFile .artifacts\build-ca\gateway-ca.crt
```

It passed Compose config/build, service health, the production doctor with zero
errors/warnings, a governed dry run and deterministic Evidence, three-store
online backup/restore, API restart persistence, and cleanup. The Compose-built
images had identical RootFS layer lists to the separately scanned final tags.
After cleanup, project-scoped container, volume, and network counts were all
zero. Repository gates also passed with 555 Python/API tests, 36 frontend tests,
frontend lint/build/bundle checks, and schema validation at 196/196.

Repository-controlled Critical/High and technical-rehearsal gates are closed.
Production remains `NO_GO` because no real signed external-control bundle,
trusted operator keyring, attachments, or physical observations were supplied.
The new verifier fails closed on missing, stale, tampered, revoked,
wrong-environment, wrong-release, or incomplete evidence and binds a future
bundle to the exact clean Git commit/tree, policy, Compose file, deployed image
digests, model digest, and environment. No production deploy, public exposure,
real credentials, or vulnerability exception was performed.

An independent read-only review returned `GO` for the repository-controlled
Item 3 after two initial Warning findings were fixed and reverified: the
keyring is now authenticated by a protected-runner digest that is included in
the signed release binding, and Git status includes untracked non-ignored
files. The reviewer retained source-to-image provenance and SARIF target binding
as Advisory because policy v1.6.0 does not yet enforce image signing,
provenance attestation, or a digest-stamped scan envelope. Production remained
`NO_GO` for the external-evidence reason above.
