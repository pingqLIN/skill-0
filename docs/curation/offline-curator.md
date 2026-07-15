# Offline Curator P2

- Status: `Experimental / P2 proposal-only boundary`
- Authority: `This English document is authoritative; the .zh-tw.md file is its human-readable companion.`

## Purpose

The offline Curator converts a validated, redacted execution trajectory and its
retrieved skill-revision snapshot into a human-reviewable draft proposal. It is
the P2 bridge between Skill-0's P1 curation contracts and the future P3
governance workflow.

The flow has two explicit steps:

```text
trajectory + retrieved skill context
  -> prepare deterministic prompt package
  -> offline/manual Curator returns a bound structured decision
  -> validate current revision and optional candidate artifact
  -> emit a dry draft curation proposal
```

## Verified Boundary

- The CLI performs no model-provider or network calls.
- The Curator cannot write to `parsed/`, `converted-skills/`, governance data,
  schemas, source packages, APIs, or the dashboard.
- Repo-local output is allowed only under ignored `output/curation/`; omitting
  `--output` prints JSON to stdout.
- Output files are create-only and cannot overwrite an existing artifact.
- Every decision is bound to the exact prompt package checksum.
- Update and delete operations fail when the target revision changed after
  prompt preparation.
- Insert and update operations require a UTF-8 candidate artifact; delete
  forbids one.
- Sensitive trajectory, context, decision, and candidate content fails closed.
- Every generated proposal remains in `governance.state = draft`.

## Contracts And Resources

| Purpose | Path |
|---|---|
| Retrieved revision snapshot | `schema/offline-curator-context.schema.json` |
| Structured Curator decision | `schema/offline-curator-decision.schema.json` |
| Draft proposal output | `schema/curation-proposal.schema.json` |
| Pinned configuration | `curation/manifests/offline-curator-v1.json` |
| Prompt template | `curation/prompts/offline-curator-v1.md` |

The manifest pins the prompt checksum, operation set, schemas, fail-closed
checks, and `dry_proposal_only` output mode. Prompt packages normalize template
line endings before hashing so their identity is stable across Windows and
POSIX checkouts.

## Prepare A Prompt Package

```powershell
python tools/offline_curator.py prepare `
  --trajectory tests/fixtures/curation_contracts/valid/execution-trajectory.json `
  --skill-context tests/fixtures/offline_curator/skill-context.json `
  --model-id local-offline-model `
  --output output/curation/prompt-package.json
```

The skill context must exactly match the trajectory's retrieved skill order and
revision IDs. The command validates both inputs before rendering the package.

## Build A Dry Proposal

An offline or manual Curator returns JSON conforming to
`offline-curator-decision.schema.json`. Its `prompt_package_checksum` must equal
the checksum in the prepared package. Insert and update decisions also provide a
candidate artifact as a separate local file.

```powershell
python tools/offline_curator.py propose `
  --prompt-package output/curation/prompt-package.json `
  --decision path/to/offline-decision.json `
  --current-context path/to/current-skill-context.json `
  --candidate-artifact path/to/candidate/SKILL.md `
  --output output/curation/draft-proposal.json
```

For delete decisions, omit `--candidate-artifact`. Use a new output filename for
each run because P2 output never overwrites an existing file.

## Unknown And Deferred

P2 does not call an LLM, judge proposal quality, run candidate ARD analysis,
search the full repository for duplicates or conflicts, persist proposals,
request approval, create revisions, or mutate a SkillRepo. Proposal validations
for ARD, duplicate, and conflict therefore remain `not_run`.

Those capabilities belong to later review gates. In particular, no P2 artifact
may be interpreted as approved or promoted.
