# DCP WBC integration lab

This public repository is the inert WBC-like integration twin for Stage 2 of
the DCP v2 program. It contains a provider-neutral mechanical Release Train, a
versioned Selectel deploy adapter and a tiny HTTP target that reports only
health and immutable deployment provenance. It contains no WBC business
behavior, business data, production route or DCP runtime integration.

## Bootstrap exception

The initial `main` commit is the sole owner-authorized empty-repository
bootstrap exception. It exists only to establish the baseline workflow, target
spec, inert target, qualification-only issuer, mechanical Release Train,
deploy adapter, tests and repository instructions needed for ordinary pull
requests. Every substantive successor uses an ordinary ready PR, exact-head
`baseline`, a real context-free semantic/security review and the repository-
owned Release Train.

Authority: `orenvlad-ai/dev-control-plane` PR #245, merged at
`86dfdb0f66889494219da7fc60351c5cee38660d`.

The only active issuer in Stage 2/3 is `qualification/v1`, pinned to actor
`orenvlad-ai`. The DCP issuer is absent. Both issuers are never active together.

## Target

- repository: `orenvlad-ai/dcp-wbc-integration-lab` (`1340359100`)
- base: `main`
- required check: `baseline`
- environment: `dcp-wbc-integration-lab-selectel`
- service: `dcp-wbc-integration-lab`
- endpoint: loopback-only `127.0.0.1:18321`
- deploy root: `/opt/dcp-wbc-integration-lab`
- retention: at most current/previous releases; proof artifacts 90 days

The Release Train never decides semantics, owns no queue, synchronizes no
branch and performs no retry. Drift produces immutable
`readmission_required`; an exact admitted head may merge once and is
nonterminal until the exact artifact is installed, started and proven by
health plus provenance readback.
