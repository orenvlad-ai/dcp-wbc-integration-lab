#!/usr/bin/env python3
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = {
    "repository": "orenvlad-ai/dcp-wbc-integration-lab",
    "repository_id": 1340359100,
    "base": "main",
    "required_check": "baseline",
    "environment": "dcp-wbc-integration-lab-selectel",
    "service": "dcp-wbc-integration-lab",
    "listener": "127.0.0.1:18321",
    "deploy_root": "/opt/dcp-wbc-integration-lab",
    "dcp_issuer": "off",
    "artifact_retention_days": 90,
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    spec = json.loads((ROOT / "target-spec.json").read_text())
    for key, value in EXPECTED.items():
        if spec.get(key) != value:
            fail(f"target spec drift: {key}")
    if spec.get("issuer") != {
        "actor": "orenvlad-ai",
        "event": "workflow_dispatch",
        "kind": "qualification/v1",
    }:
        fail("qualification issuer drift")
    if spec.get("release_actor") != "github-actions[bot]":
        fail("release actor drift")
    if spec.get("qualification_matrix") != {
        "cases": [
            "valid",
            "head_drift",
            "main_drift",
            "wrong_identity",
            "duplicate_manifest_event",
            "artifact_mismatch",
            "probe_failure",
        ],
        "idempotency": "equal-manifest-reuses-terminal-proof/v1",
        "negative_effects": "no-ref-or-deploy/v1",
    }:
        fail("qualification matrix drift")
    if spec.get("resource_limits") != {
        "cpu_quota_percent": 50,
        "memory_max_bytes": 536870912,
        "open_files_max": 1024,
        "releases_max": 2,
        "tasks_max": 64,
    }:
        fail("resource limits drift")

    workflow = (ROOT / ".github/workflows/release-train.yml").read_text()
    workflow_lower = workflow.lower()
    forbidden = ["git rebase", "update-branch", "--force", "force-with-lease", "retry"]
    for token in forbidden:
        if token in workflow_lower:
            fail(f"forbidden Release Train token: {token}")
    for token in [
        "workflow_dispatch",
        "manifest_b64",
        "retention-days: 90",
        "detect equal terminal replay",
        "controlled artifact-digest mismatch",
        "controlled exact probe failure",
        "qualification-evidence-",
    ]:
        if token not in workflow_lower:
            fail(f"missing Release Train token: {token}")

    release_core = (ROOT / "scripts/release_train.py").read_text()
    for token in [
        '"readmission_required"',
        '"equal_duplicate"',
        '"deployment_failure"',
        '"ref_updates": 0',
        '"release_artifacts": 0',
        '"deploys": 0',
        "conflicting terminal proof artifacts",
    ]:
        if token not in release_core:
            fail(f"missing qualification core boundary: {token}")
    if "orenvlad-ai/wb-core" in release_core or "DCP_AO" in release_core:
        fail("qualification core contains a foreign target or DCP authority")

    receiver = (ROOT / "deploy/dcp-wbc-lab-deploy").read_text()
    for token in [
        "DCP_WBC_LAB_DEPLOY_V1",
        "DCP_WBC_LAB_PROBE_V1",
        "127.0.0.1:18321",
        "build.sha",
        "service=dcp-wbc-integration-lab.service",
        'systemctl --user restart "$service"',
    ]:
        if token not in receiver:
            fail(f"missing receiver boundary: {token}")
    if re.search(r"\b(eval|sudo)\b", receiver):
        fail("receiver contains privilege or eval surface")

    service = (ROOT / "deploy/dcp-wbc-integration-lab.service").read_text()
    for token in [
        "CPUQuota=50%",
        "MemoryMax=512M",
        "TasksMax=64",
        "LimitNOFILE=1024",
        "IPAddressDeny=any",
        "IPAddressAllow=localhost",
        "InaccessiblePaths=/opt/luchiki-landing /opt/wb-core-runtime /opt/wb-ai /opt/wb-ai-repo /opt/wb-web-bot",
    ]:
        if token not in service:
            fail(f"missing service boundary: {token}")

    print("PASS target spec, issuer, Release Train and deploy boundaries")


if __name__ == "__main__":
    main()
