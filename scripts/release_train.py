#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
from datetime import datetime, timezone


REPOSITORY = "orenvlad-ai/dcp-wbc-integration-lab"
REPOSITORY_ID = 1340359100
TARGET_SPEC = "dcp-wbc-integration-lab/v1"
QUALIFICATION_CASES = {
    "valid",
    "head_drift",
    "main_drift",
    "wrong_identity",
    "artifact_mismatch",
    "probe_failure",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_digest(value: dict, digest_key: str) -> str:
    body = {key: item for key, item in value.items() if key != digest_key}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def manifest_digest(value: dict) -> str:
    return canonical_digest(value, "manifest_digest")


def proof_digest(value: dict) -> str:
    return canonical_digest(value, "proof_digest")


def gh(*args: str) -> object:
    result = subprocess.run(
        ["gh", "api", *args], check=True, text=True, capture_output=True
    )
    return json.loads(result.stdout)


def append_output(path: pathlib.Path, **values: object) -> None:
    with path.open("a") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def unique_artifact_file(root: pathlib.Path, name: str) -> pathlib.Path:
    candidates = [
        path
        for path in root.rglob(name)
        if path.is_file() and not path.is_symlink()
    ]
    if len(candidates) != 1:
        raise SystemExit(f"terminal proof artifact has {len(candidates)} {name} files")
    return candidates[0]


def write_evidence(
    path: pathlib.Path,
    kind: str,
    reason: str,
    manifest: dict,
    *,
    phase: str = "validation",
    observed: dict | None = None,
    effects: dict | None = None,
) -> None:
    value = {
        "protocol": "dcp-release-evidence/v1",
        "target_spec": TARGET_SPEC,
        "qualification_case": manifest.get("qualification_case", "stage3_setup"),
        "kind": kind,
        "phase": phase,
        "reason": reason,
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "manifest_digest": manifest.get("manifest_digest", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "observed": observed or {},
        "effects": effects
        or {
            "ref_updates": 0,
            "merges": 0,
            "release_artifacts": 0,
            "deploys": 0,
            "terminal_proofs": 0,
        },
        "observed_at": now(),
    }
    value["evidence_digest"] = canonical_digest(value, "evidence_digest")
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def stop(
    path: pathlib.Path,
    kind: str,
    reason: str,
    manifest: dict,
    *,
    phase: str = "validation",
    observed: dict | None = None,
) -> None:
    write_evidence(path, kind, reason, manifest, phase=phase, observed=observed)
    raise SystemExit(reason)


def require(
    condition: bool,
    path: pathlib.Path,
    reason: str,
    manifest: dict,
    *,
    observed: dict | None = None,
) -> None:
    if not condition:
        stop(path, "validation_failure", reason, manifest, observed=observed)


def validate(args: argparse.Namespace) -> None:
    manifest_path = pathlib.Path(args.manifest)
    evidence_path = pathlib.Path(args.evidence)
    manifest = json.loads(manifest_path.read_text())
    qualification_case = manifest.get("qualification_case", "stage3_setup")
    require(
        qualification_case in QUALIFICATION_CASES or qualification_case == "stage3_setup",
        evidence_path,
        "qualification_case",
        manifest,
    )
    required = {
        "protocol": "dcp-release-manifest/v1",
        "target_spec": TARGET_SPEC,
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
        require(
            manifest.get(key) == expected,
            evidence_path,
            f"manifest_{key}",
            manifest,
            observed={"field": key, "expected": expected, "actual": manifest.get(key)},
        )
    require(
        manifest.get("manifest_digest") == manifest_digest(manifest),
        evidence_path,
        "manifest_digest",
        manifest,
    )
    require(
        manifest.get("issuer")
        == {
            "actor": "orenvlad-ai",
            "event": "workflow_dispatch",
            "kind": "qualification/v1",
        },
        evidence_path,
        "issuer",
        manifest,
    )
    require(os.environ.get("GITHUB_ACTOR") == "orenvlad-ai", evidence_path, "actor", manifest)
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch", evidence_path, "event", manifest)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, evidence_path, "workflow_repository", manifest)

    repo = gh(f"repos/{REPOSITORY}")
    require(
        repo.get("id") == REPOSITORY_ID and repo.get("visibility") == "public",
        evidence_path,
        "repository_identity",
        manifest,
    )
    pr_number = manifest.get("pr_number")
    require(isinstance(pr_number, int) and pr_number > 0, evidence_path, "pr_number", manifest)
    pr = gh(f"repos/{REPOSITORY}/pulls/{pr_number}")
    require(pr.get("state") == "open" and pr.get("draft") is False, evidence_path, "pr_state", manifest)
    require(pr["base"]["ref"] == "main", evidence_path, "pr_base", manifest)
    require(pr["head"]["repo"]["full_name"] == REPOSITORY, evidence_path, "head_repository", manifest)
    if pr["head"]["sha"] != manifest.get("admitted_head"):
        stop(
            evidence_path,
            "readmission_required",
            "head_drift",
            manifest,
            observed={
                "expected_head": manifest.get("admitted_head"),
                "current_head": pr["head"]["sha"],
                "current_main": gh(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"],
            },
        )
    if qualification_case == "head_drift":
        stop(evidence_path, "validation_failure", "expected_head_drift_not_observed", manifest)
    ref = gh(f"repos/{REPOSITORY}/git/ref/heads/main")
    if ref["object"]["sha"] != manifest.get("main_snapshot"):
        stop(
            evidence_path,
            "readmission_required",
            "main_drift",
            manifest,
            observed={
                "expected_main": manifest.get("main_snapshot"),
                "current_main": ref["object"]["sha"],
                "current_head": pr["head"]["sha"],
            },
        )
    if qualification_case == "main_drift":
        stop(evidence_path, "validation_failure", "expected_main_drift_not_observed", manifest)
    require(pr.get("mergeable") is True and pr.get("mergeable_state") == "clean", evidence_path, "mergeability", manifest)

    checks = gh(f"repos/{REPOSITORY}/commits/{manifest['admitted_head']}/check-runs")
    exact_checks = [check for check in checks.get("check_runs", []) if check.get("name") == "baseline"]
    require(len(exact_checks) == 1, evidence_path, "check_cardinality", manifest)
    check = exact_checks[0]
    require(
        check.get("id") == manifest.get("check_run_id")
        and check.get("conclusion") == "success",
        evidence_path,
        "check_identity",
        manifest,
        observed={"current_check_run_id": check.get("id"), "conclusion": check.get("conclusion")},
    )

    review = gh(f"repos/{REPOSITORY}/pulls/{pr_number}/reviews/{manifest.get('review_id')}")
    require(review.get("commit_id") == manifest["admitted_head"], evidence_path, "review_head", manifest)
    require(review.get("state") in {"COMMENTED", "APPROVED"}, evidence_path, "review_state", manifest)
    require("no findings" in (review.get("body") or "").lower(), evidence_path, "review_verdict", manifest)
    review_hash = hashlib.sha256((review.get("body") or "").encode()).hexdigest()
    require(review_hash == manifest.get("review_digest"), evidence_path, "review_digest", manifest)

    query = f'''query {{ repository(owner:"orenvlad-ai", name:"dcp-wbc-integration-lab") {{ pullRequest(number:{pr_number}) {{ reviewThreads(first:100) {{ nodes {{ isResolved }} }} }} }} }}'''
    threads = gh("graphql", "-f", f"query={query}")
    unresolved = [
        node
        for node in threads["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        if not node["isResolved"]
    ]
    require(not unresolved, evidence_path, "unresolved_threads", manifest)
    if qualification_case == "wrong_identity":
        stop(evidence_path, "validation_failure", "expected_wrong_identity_not_observed", manifest)

    append_output(
        pathlib.Path(args.github_output),
        manifest_digest=manifest["manifest_digest"],
        pr_number=pr_number,
        admitted_head=manifest["admitted_head"],
        qualification_case=qualification_case,
    )
    print(f"validated manifest {manifest['manifest_digest']}")


def replay(args: argparse.Namespace) -> None:
    manifest_path = pathlib.Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    output = pathlib.Path(args.github_output)
    if manifest.get("manifest_digest") != manifest_digest(manifest):
        append_output(output, replayed="false")
        return
    digest = manifest["manifest_digest"]
    artifact_name = f"deploy-proof-{digest}"
    response = gh(f"repos/{REPOSITORY}/actions/artifacts?name={artifact_name}&per_page=100")
    artifacts = [artifact for artifact in response.get("artifacts", []) if not artifact.get("expired")]
    if not artifacts:
        append_output(output, replayed="false")
        return
    if len(artifacts) != 1:
        raise SystemExit("conflicting terminal proof artifacts")
    artifact = artifacts[0]
    run_id = artifact.get("workflow_run", {}).get("id")
    if not isinstance(run_id, int):
        raise SystemExit("terminal proof artifact lacks workflow identity")
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            REPOSITORY,
            "--name",
            artifact_name,
            "--dir",
            str(out_dir),
        ],
        check=True,
    )
    prior_manifest_path = unique_artifact_file(out_dir, "manifest.json")
    prior_proof_path = unique_artifact_file(out_dir, "deploy-proof.json")
    prior_manifest = json.loads(prior_manifest_path.read_text())
    prior_proof = json.loads(prior_proof_path.read_text())
    if prior_manifest != manifest:
        raise SystemExit("conflicting manifest bytes for terminal proof")
    if prior_proof.get("admission_digest") != digest:
        raise SystemExit("terminal proof admission digest drift")
    if prior_proof.get("proof_digest") != proof_digest(prior_proof):
        raise SystemExit("terminal proof digest drift")
    replay_evidence = {
        "protocol": "dcp-release-replay/v1",
        "target_spec": TARGET_SPEC,
        "qualification_case": "duplicate_manifest_event",
        "kind": "equal_duplicate",
        "manifest_digest": digest,
        "proof_digest": prior_proof["proof_digest"],
        "source_run_id": str(run_id),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "effects": {
            "ref_updates": 0,
            "merges": 0,
            "release_artifacts": 0,
            "deploys": 0,
            "terminal_proofs_reused": 1,
            "terminal_proofs_created": 0,
        },
        "observed_at": now(),
    }
    replay_evidence["evidence_digest"] = canonical_digest(replay_evidence, "evidence_digest")
    (out_dir / "replay-evidence.json").write_text(
        json.dumps(replay_evidence, sort_keys=True, indent=2) + "\n"
    )
    append_output(
        output,
        replayed="true",
        manifest_digest=digest,
        proof_digest=prior_proof["proof_digest"],
        source_run_id=run_id,
    )
    print(f"equal duplicate reuses proof {prior_proof['proof_digest']}")


def failure(args: argparse.Namespace) -> None:
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    observed = {
        "merge_sha": args.merge_sha,
        "artifact_digest": args.artifact_sha,
        "deployed_sha": args.deployed_sha,
    }
    if args.receipt and pathlib.Path(args.receipt).is_file():
        observed["receipt_digest"] = hashlib.sha256(
            pathlib.Path(args.receipt).read_bytes()
        ).hexdigest()
    write_evidence(
        pathlib.Path(args.evidence),
        "deployment_failure",
        args.reason,
        manifest,
        phase=args.phase,
        observed=observed,
    )


def make_proof(args: argparse.Namespace) -> None:
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    proof = {
        "protocol": "dcp-deployment-proof/v1",
        "target_spec": manifest["target_spec"],
        "qualification_case": manifest.get("qualification_case", "stage3_setup"),
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
        "effects": {
            "ref_updates": 1,
            "merges": 1,
            "release_artifacts": 1,
            "deploys": 1,
            "terminal_proofs": 1,
        },
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
            "published": now(),
        },
    }
    receipt_hash = hashlib.sha256(pathlib.Path(args.probe_receipt).read_bytes()).hexdigest()
    for probe in proof["probes"]:
        probe["evidence_digest"] = receipt_hash
    proof["proof_digest"] = proof_digest(proof)
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
    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("--manifest", required=True)
    replay_parser.add_argument("--output-dir", required=True)
    replay_parser.add_argument("--github-output", required=True)
    replay_parser.set_defaults(func=replay)
    failure_parser = sub.add_parser("failure")
    failure_parser.add_argument("--manifest", required=True)
    failure_parser.add_argument("--evidence", required=True)
    failure_parser.add_argument("--phase", required=True)
    failure_parser.add_argument("--reason", required=True)
    failure_parser.add_argument("--merge-sha", default="")
    failure_parser.add_argument("--artifact-sha", default="")
    failure_parser.add_argument("--deployed-sha", default="")
    failure_parser.add_argument("--receipt", default="")
    failure_parser.set_defaults(func=failure)
    proof_parser = sub.add_parser("proof")
    proof_parser.add_argument("--manifest", required=True)
    proof_parser.add_argument("--probe-receipt", required=True)
    proof_parser.add_argument("--output", required=True)
    proof_parser.set_defaults(func=make_proof)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
