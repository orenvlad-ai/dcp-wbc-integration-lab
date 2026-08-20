# Repository rules

This repository is the isolated DCP v2 integration twin, not WBC or production.

- Preserve the completed Stage 2/3 evidence and `target-spec.json` identities.
- Stage 5 retires `qualification/v1` and permits only exact `dcp/v2`, actor
  `orenvlad-ai`, `repository_dispatch`, event type `dcp-admission-v2` and target
  spec `dcp-wbc-integration-lab/v2`. The one-time reviewed
  `qualification/handoff-v1` path can merge only its own open exact-head PR,
  performs zero deploys, and disables this workflow before DCP enable readback.
- Every substantive change uses a ready PR, exact-head `baseline`, a real
  context-free semantic/security review with no unresolved findings and one
  exact manifest.
- The Release Train is mechanical: no semantic decision, second queue,
  auto-sync, rebase, update-branch, force-push, head substitution or retry.
- Merge is nonterminal until artifact/source/deployed SHA, environment,
  service, probes, actor/run/timestamps and proof digest agree.
- The persistent service is loopback-only and contains no secret or data.
- Historical Stage 3 negative fixtures remain immutable evidence; they publish
  typed immutable evidence, make at most one bounded adapter call and preserve
  the last proven deployment. Equal replay reuses one terminal proof and must
  create no second merge or deploy.
- Models never merge, release, deploy, use SSH, read secrets, touch Selectel,
  WBC, production or business data. Only the repository Release Train may
  merge/build/deploy an exact DCP-issued admitted head.
- Never print deployment credentials. Technical completion is not owner
  acceptance.
