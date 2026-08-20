# Stage 2 persistent deployment boundary

Authority is `orenvlad-ai/dev-control-plane` PR #245, merged as
`86dfdb0f66889494219da7fc60351c5cee38660d`.

## Repository controls

- repository: public `orenvlad-ai/dcp-wbc-integration-lab`, ID `1340359100`
- bootstrap: `d5455175a3798a382796003fd6053e8b6b7c1534`
- main ruleset: `Stage 2 governed main`, ID `21077248`, active, no bypass
- main requirements: PR, exact up-to-date `baseline`, thread resolution,
  squash-only merge, no deletion or non-fast-forward update
- environment: `dcp-wbc-integration-lab-selectel`, ID `20234191757`, protected
  branches only

The empty-repository bootstrap above is the sole direct-main exception. The
qualification issuer is the only Stage 2/3 issuer and dispatches one immutable
exact-head manifest. The mechanical Release Train makes no semantic decision,
creates no queue and never synchronizes, rebases, updates or force-pushes a
branch. Base or head drift produces immutable `readmission_required` evidence.

## Destination controls

- existing Selectel server UUID: `96be74db-785f-4653-85a8-a4e7c1d3ccdf`
- public/private IP: `178.72.152.177` / `192.168.0.161`
- environment/service: `dcp-wbc-integration-lab-selectel` /
  `dcp-wbc-integration-lab`
- account/root: unprivileged `dcp-wbc-lab` /
  `/opt/dcp-wbc-integration-lab`
- network: SSH through the existing port and HTTP only on
  `127.0.0.1:18321`; no new public application port or firewall rule
- ceiling: 50% CPU, 512 MiB memory, 64 tasks, 1024 open files
- retention: current plus previous release and 90-day immutable proof artifacts

The forced deploy credential accepts only the versioned deploy/probe protocol.
It cannot select a command or path. The shipped binary is never executed by
the SSH receiver: validated manifest merge identity is stored as data and
execution occurs only in the hardened systemd unit. That unit makes the protected
`/opt/luchiki-landing` co-tenant and all retired legacy-WBC roots inaccessible.
The service has no business data, WBC secret, DCP authority or production
route.

The server, Selectel project, shared OS/network, nginx and the protected
`лучики-добра.рф` application remain outside the lab rollback boundary. No VM
or other paid Selectel resource is created.

## Stage 3 fixed qualification behavior

The owner-authorized Stage 3 harness keeps the exact Stage 2 destination and
credential. Its seven cases are valid release/deploy, PR-head drift, main
drift, wrong repository/base/PR/check identity, equal duplicate delivery,
artifact-digest mismatch and probe failure. Every negative case publishes an
immutable typed evidence artifact with zero merge/deploy effects. Equal replay
reuses the original canonical deployment proof and produces zero second merge
or deployment.

The two controlled adapter failures use exactly one forced-command call. The
artifact mismatch is rejected before activation; the probe mismatch is
read-only. Neither case retries, redeploys, changes the destination, touches a
protected co-tenant or claims false terminal success. The final persistent
service must remain the last exact successful release proven by health and
provenance.
