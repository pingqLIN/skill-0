# Runtime v4 Governance Admission

Runtime v4 has two distinct governance boundaries:

1. **Run admission** proves that the exact canonical parsed JSON is the artifact represented by the current approved governance revision.
2. **Action policy and HITL** decide whether an admitted run may execute or recover each action.

Neither boundary substitutes for the other.

## Identity and authority

- `skills.skill_id` is the internal governance UUID.
- `skills.canonical_skill_id` is the explicit unique link to `parsed/*.json -> meta.skill_id`.
- `skill_revisions.artifact_digest` is the canonical SHA-256 of the complete parsed JSON.
- `skills.current_revision_id` selects the authoritative revision.
- Runtime admission reads `skill_revisions.status`; it never authorizes from the mutable `skills.status` projection.
- Runtime contracts do not contain governance approval fields.

Legacy rows without a canonical identity or artifact digest are intentionally non-runnable.

## Binding and approval workflow

The current revision must still be `pending` when its Runtime identity is bound:

```http
POST /api/reviews/{governance_skill_id}/runtime-bind
Authorization: Bearer <core-issued-jwt>
Content-Type: application/json

{
  "canonical_skill_id": "claude__skill__example"
}
```

The Dashboard governance API loads the matching canonical JSON server-side, computes its digest, and records the reviewer from JWT `sub`. The request cannot provide the actor or digest.

After binding, use the existing governance approval endpoint. Any new revision resets approval and artifact binding to `pending`/unbound, so it must be rebound and re-reviewed.

## Create and resume semantics

On both create and resume, the core Runtime gate requires:

- exact canonical skill ID binding;
- current revision ownership and `is_current=1`;
- current revision status `approved`;
- exact canonical artifact digest;
- matching version;
- approver identity and timestamp.

The governance revision ID is persisted in `runtime_execution_bases` and is included in the keyed execution digest through the preflight attestation. Revocation, supersession, or canonical JSON drift denies resume before its one-time resume claim is consumed.

## Dashboard boundary

The web Dashboard calls the core `/api/runs/*` endpoints directly through a dedicated authenticated client. It does not proxy Runtime decisions through the Dashboard API and does not mirror Runtime decisions into `governance.db`.

- Skill/revision approval remains authoritative in `governance.db`.
- Runtime HITL decisions remain authoritative in `runtime.db`.
- Both APIs accept the core-issued JWT; Runtime decision actor authorization is additionally constrained by `SKILL0_RUNTIME_DECISION_ACTORS`.
- Approve/confirm actions only record decisions. The UI never automatically resumes or recovers a run.

Per-run Evidence includes `governance_ref` so operators can verify the admitted revision without reading either SQLite file directly.
