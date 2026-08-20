#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone


REPOSITORY = "orenvlad-ai/dcp-wbc-integration-lab"
REPOSITORY_ID = 1340359100


def canonical_digest(value: dict) -> str:
    body = {key: item for key, item in value.items() if key != "manifest_digest"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def gh(*args: str) -> object:
    result = subprocess.run(
        ["gh", "api", *args], check=True, text=True, capture_output=True
    )
    return json.loads(result.stdout)


def evidence(path: pathlib.Path, kind: str, reason: str, manifest: dict) -> None:
    value = {
        "kind": kind,
        "reason": reason,
        "repository": REPOSITORY,
        "manifest_digest": manifest.get("manifest_digest", ""),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    value["evidence_digest"] = canonical_digest(value)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def stop(path: pathlib.Path, kind: str, reason: str, manifest: dict) -> None:
    evidence(path, kind, reason, manifest)
    raise SystemExit(reason)


def require(condition: bool, path: pathlib.Path, reason: str, manifest: dict) -> None:
    if not condition:
        stop(path, "validation_failure", reason, manifest)


def validate(args: argparse.Namespace) -> None:
    manifest_path = pathlib.Path(args.manifest)
    evidence_path = pathlib.Path(args.evidence)
    manifest = json.loads(manifest_path.read_text())
    required = {
        "protocol": "dcp-release-manifest/v1",
        "target_spec": "dcp-wbc-integration-lab/v1",
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "base": "main",
        "required_check": "baseline",
        "profile": "persistent-lab",
        "environment": "dcp-wbc-integration-lab-selectel",
        "service": "dcp-wbc-integration-lab",
        "adapter": "selectel-systemd/v1",
    }
    for key, expected in required.items():
        require(manifest.get(key) == expected, evidence_path, f"manifest_{key}", manifest)
    require(manifest.get("manifest_digest") == canonical_digest(manifest), evidence_path, "manifest_digest", manifest)
    require(manifest.get("issuer") == {"actor": "orenvlad-ai", "event": "workflow_dispatch", "kind": "qualification/v1"}, evidence_path, "issuer", manifest)
    require(os.environ.get("GITHUB_ACTOR") == "orenvlad-ai", evidence_path, "actor", manifest)
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch", evidence_path, "event", manifest)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, evidence_path, "workflow_repository", manifest)

    repo = gh(f"repos/{REPOSITORY}")
    require(repo.get("id") == REPOSITORY_ID and repo.get("visibility") == "public", evidence_path, "repository_identity", manifest)
    pr_number = manifest.get("pr_number")
    require(isinstance(pr_number, int) and pr_number > 0, evidence_path, "pr_number", manifest)
    pr = gh(f"repos/{REPOSITORY}/pulls/{pr_number}")
    require(pr.get("state") == "open" and pr.get("draft") is False, evidence_path, "pr_state", manifest)
    require(pr["base"]["ref"] == "main", evidence_path, "pr_base", manifest)
    require(pr["head"]["repo"]["full_name"] == REPOSITORY, evidence_path, "head_repository", manifest)
    if pr["head"]["sha"] != manifest.get("admitted_head"):
        stop(evidence_path, "readmission_required", "head_drift", manifest)
    ref = gh(f"repos/{REPOSITORY}/git/ref/heads/main")
    if ref["object"]["sha"] != manifest.get("main_snapshot"):
        stop(evidence_path, "readmission_required", "main_drift", manifest)
    require(pr.get("mergeable") is True and pr.get("mergeable_state") == "clean", evidence_path, "mergeability", manifest)

    checks = gh(f"repos/{REPOSITORY}/commits/{manifest['admitted_head']}/check-runs")
    exact_checks = [check for check in checks.get("check_runs", []) if check.get("name") == "baseline"]
    require(len(exact_checks) == 1, evidence_path, "check_cardinality", manifest)
    check = exact_checks[0]
    require(check.get("id") == manifest.get("check_run_id") and check.get("conclusion") == "success", evidence_path, "check_identity", manifest)

    review = gh(f"repos/{REPOSITORY}/pulls/{pr_number}/reviews/{manifest.get('review_id')}")
    require(review.get("commit_id") == manifest["admitted_head"], evidence_path, "review_head", manifest)
    require(review.get("state") in {"COMMENTED", "APPROVED"}, evidence_path, "review_state", manifest)
    require("no findings" in (review.get("body") or "").lower(), evidence_path, "review_verdict", manifest)
    review_digest = hashlib.sha256((review.get("body") or "").encode()).hexdigest()
    require(review_digest == manifest.get("review_digest"), evidence_path, "review_digest", manifest)

    query = f'''query {{ repository(owner:"orenvlad-ai", name:"dcp-wbc-integration-lab") {{ pullRequest(number:{pr_number}) {{ reviewThreads(first:100) {{ nodes {{ isResolved }} }} }} }} }}'''
    threads = gh("graphql", "-f", f"query={query}")
    unresolved = [node for node in threads["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"] if not node["isResolved"]]
    require(not unresolved, evidence_path, "unresolved_threads", manifest)

    output = pathlib.Path(args.github_output)
    with output.open("a") as handle:
        handle.write(f"manifest_digest={manifest['manifest_digest']}\n")
        handle.write(f"pr_number={pr_number}\n")
        handle.write(f"admitted_head={manifest['admitted_head']}\n")
    print(f"validated manifest {manifest['manifest_digest']}")


def make_proof(args: argparse.Namespace) -> None:
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    proof = {
        "protocol": "dcp-deployment-proof/v1",
        "target_spec": manifest["target_spec"],
        "task_id": manifest["task_id"],
        "revision_id": manifest["revision_id"],
        "admission_id": manifest["admission_id"],
        "admission_sequence": manifest["admission_sequence"],
        "admission_digest": manifest["manifest_digest"],
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "base": "main",
        "pr_number": manifest["pr_number"],
        "admitted_head": manifest["admitted_head"],
        "check_run_id": manifest["check_run_id"],
        "review_id": manifest["review_id"],
        "review_digest": manifest["review_digest"],
        "merge_sha": os.environ["MERGE_SHA"],
        "merge_actor": "github-actions[bot]",
        "artifact_id": f"dcp-wbc-integration-lab-{os.environ['MERGE_SHA']}",
        "artifact_media_type": "application/gzip",
        "artifact_source_sha": os.environ["MERGE_SHA"],
        "artifact_digest": os.environ["ARTIFACT_SHA"],
        "deployed_sha": os.environ["MERGE_SHA"],
        "environment": "dcp-wbc-integration-lab-selectel",
        "service": "dcp-wbc-integration-lab",
        "probes": [
            {"name": "healthz", "target": "loopback", "result": "success"},
            {"name": "provenance", "target": "loopback", "result": "success"},
            {"name": "post_job_readback", "target": "forced-ssh-probe", "result": "success"},
        ],
        "workflow": "release-train.yml",
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "job": os.environ["GITHUB_JOB"],
        "dispatch_actor": os.environ["GITHUB_ACTOR"],
        "timestamps": {
            "validated": os.environ["VALIDATED_AT"],
            "merged": os.environ["MERGED_AT"],
            "built": os.environ["BUILT_AT"],
            "installed": os.environ["INSTALLED_AT"],
            "probed": os.environ["PROBED_AT"],
            "published": datetime.now(timezone.utc).isoformat(),
        },
    }
    probe_digest = hashlib.sha256(pathlib.Path(args.probe_receipt).read_bytes()).hexdigest()
    for probe in proof["probes"]:
        probe["evidence_digest"] = probe_digest
    proof["proof_digest"] = canonical_digest(proof)
    pathlib.Path(args.output).write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n")
    print(proof["proof_digest"])


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--manifest", required=True)
    validate_parser.add_argument("--evidence", required=True)
    validate_parser.add_argument("--github-output", required=True)
    validate_parser.set_defaults(func=validate)
    proof_parser = sub.add_parser("proof")
    proof_parser.add_argument("--manifest", required=True)
    proof_parser.add_argument("--probe-receipt", required=True)
    proof_parser.add_argument("--output", required=True)
    proof_parser.set_defaults(func=make_proof)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
