# Shared Documentation Source

This directory is the source of truth for documentation that should be reused across both:

- `skill-0`
- `skill-0-GUI`

The rule is simple:

- keep repository-specific product, deployment, roadmap, and status notes in each repository
- keep stable cross-repository contracts here

Suitable shared documents include:

- parser contract
- schema contract
- canonical vs standalone mode semantics
- shared terminology
- evidence/risk language used by both review surfaces
- cross-repo session coordination rules

Unsuitable shared documents include:

- release notes
- project status reports
- deployment steps tied to one runtime
- UI walkthroughs tied only to `skill-0-GUI`
- API/dashboard operations tied only to `skill-0`

`skill-0-GUI` should mirror selected files from this directory into its own `docs/shared/` directory by running:

```bash
npm run docs:sync
```

The mirrored copies should be treated as vendored contract documents, not independently authored files.
