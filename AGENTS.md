# Repository rules

This repository is an inert qualification target, not WBC or DCP runtime.

- Preserve `target-spec.json` identity and the qualification-only issuer.
- Never add WBC business behavior, business data, production credentials or a
  DCP issuer during Stage 2/3.
- Every substantive change uses a ready PR, exact-head `baseline`, a real
  context-free semantic/security review with no unresolved findings and one
  exact manifest.
- The Release Train is mechanical: no semantic decision, second queue,
  auto-sync, rebase, update-branch, force-push, head substitution or retry.
- Merge is nonterminal until artifact/source/deployed SHA, environment,
  service, probes, actor/run/timestamps and proof digest agree.
- The persistent service is loopback-only and contains no secret or data.
- Stage 3 negative fixtures are fixed by `target-spec.json`; they publish
  typed immutable evidence, make at most one bounded adapter call and preserve
  the last proven deployment. Equal replay reuses one terminal proof and must
  create no second merge or deploy.
- Never print deployment credentials. Technical completion is not owner
  acceptance.
