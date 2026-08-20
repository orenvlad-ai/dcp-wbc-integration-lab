#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import subprocess
from datetime import datetime, timezone


REPOSITORY = "orenvlad-ai/dcp-wbc-integration-lab"


def gh(*args: str) -> object:
    result = subprocess.run(["gh", "api", *args], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def digest(value: dict) -> str:
    body = {key: item for key, item in value.items() if key != "manifest_digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="qualification-only manifest issuer")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--review-id", type=int, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--revision-id", required=True)
    parser.add_argument("--admission-id", required=True)
    parser.add_argument("--sequence", type=int, required=True)
    args = parser.parse_args()

    user = gh("user")
    if user.get("login") != "orenvlad-ai":
        raise SystemExit("qualification issuer actor drift")
    repo = gh(f"repos/{REPOSITORY}")
    if repo.get("id") != 1340359100 or repo.get("visibility") != "public":
        raise SystemExit("repository identity drift")
    pr = gh(f"repos/{REPOSITORY}/pulls/{args.pr}")
    if pr.get("state") != "open" or pr.get("draft") is not False:
        raise SystemExit("PR is not ready/open")
    if pr["base"]["ref"] != "main" or pr["head"]["repo"]["full_name"] != REPOSITORY:
        raise SystemExit("PR topology drift")
    head = pr["head"]["sha"]
    main_sha = gh(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"]
    checks = gh(f"repos/{REPOSITORY}/commits/{head}/check-runs").get("check_runs", [])
    baseline = [check for check in checks if check.get("name") == "baseline"]
    if len(baseline) != 1 or baseline[0].get("conclusion") != "success":
        raise SystemExit("exact baseline is not successful")
    review = gh(f"repos/{REPOSITORY}/pulls/{args.pr}/reviews/{args.review_id}")
    if review.get("commit_id") != head or "no findings" not in (review.get("body") or "").lower():
        raise SystemExit("exact review is not approved/no-findings evidence")

    manifest = {
        "protocol": "dcp-release-manifest/v1",
        "target_spec": "dcp-wbc-integration-lab/v1",
        "repository": REPOSITORY,
        "repository_id": 1340359100,
        "base": "main",
        "main_snapshot": main_sha,
        "task_id": args.task_id,
        "revision_id": args.revision_id,
        "pr_number": args.pr,
        "head_repository": REPOSITORY,
        "head_branch": pr["head"]["ref"],
        "admitted_head": head,
        "required_check": "baseline",
        "check_run_id": baseline[0]["id"],
        "review_id": args.review_id,
        "review_digest": hashlib.sha256((review.get("body") or "").encode()).hexdigest(),
        "admission_id": args.admission_id,
        "admission_sequence": args.sequence,
        "profile": "persistent-lab",
        "adapter": "selectel-systemd/v1",
        "environment": "dcp-wbc-integration-lab-selectel",
        "service": "dcp-wbc-integration-lab",
        "issuer": {"actor": "orenvlad-ai", "event": "workflow_dispatch", "kind": "qualification/v1"},
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest["manifest_digest"] = digest(manifest)
    encoded = base64.b64encode(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).decode()
    subprocess.run(
        [
            "gh", "workflow", "run", "release-train.yml", "--repo", REPOSITORY,
            "--ref", "main", "-f", f"manifest_b64={encoded}",
        ],
        check=True,
    )
    print(f"dispatched qualification manifest {manifest['manifest_digest']}")


if __name__ == "__main__":
    main()
