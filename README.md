# DCP WBC integration lab

This public repository is the inert WBC-like integration twin for Stage 2 of
the DCP v2 program. It contains a provider-neutral mechanical Release Train, a
versioned Selectel deploy adapter and a tiny HTTP target that reports only
health and immutable deployment provenance. It contains no WBC business
behavior, business data, production route or DCP runtime integration.

## Bootstrap exception

The initial `main` commit is the sole owner-authorized empty-repository
bootstrap exception. It exists only to establish the baseline workflow, target
spec, inert target, historical qualification issuer, mechanical Release Train,
deploy adapter, tests and repository instructions needed for ordinary pull
requests. Every substantive successor uses an ordinary ready PR, exact-head
`baseline`, a real context-free semantic/security review and the repository-
owned Release Train.

Authority: `orenvlad-ai/dev-control-plane` PR #245, merged at
`86dfdb0f66889494219da7fc60351c5cee38660d`.

Stage 2/3 used only `qualification/v1`, pinned to actor `orenvlad-ai`; those
artifacts remain immutable history. Stage 5 retires that issuer and activates
only `dcp/v2` / `repository_dispatch` / `dcp-admission-v2` for exact target spec
`dcp-wbc-integration-lab/v2`. A one-time exact-head handoff run merges the seam
without deploy and disables the workflow before the DCP enable readback, so
both issuers are never active together.

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

## Stage 3 qualification harness

The qualification-only issuer freezes seven model-free cases in
`target-spec.json`. The train validates repository, base, PR, exact head,
current main, required check, review and manifest identity before any effect.
Head or main drift writes one immutable `readmission_required` fact. An equal
terminal-manifest delivery loads and verifies the original immutable proof and
performs zero second merge or deployment. Controlled artifact-digest and probe
failures make one real call to the forced adapter, publish exact failure
evidence and leave the previously proven service running. There is no
automatic redeploy, branch synchronization or second issuer.

The fixed negative fixtures address only this repository, environment and
loopback service. They cannot select another repository, WBC, DCP runtime,
host path, command or credential. A failure artifact is evidence, never a
terminal deployment proof.
