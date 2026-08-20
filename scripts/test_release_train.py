#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).with_name("release_train.py")
SPEC = importlib.util.spec_from_file_location("release_train", MODULE_PATH)
assert SPEC and SPEC.loader
release_train = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_train)


def base_manifest() -> dict:
    value = {
        "protocol": "dcp-release-manifest/v1",
        "target_spec": "dcp-wbc-integration-lab/v1",
        "repository": release_train.REPOSITORY,
        "repository_id": release_train.REPOSITORY_ID,
        "base": "main",
        "main_snapshot": "1" * 40,
        "task_id": "stage3-test",
        "revision_id": "stage3-test-r1",
        "pr_number": 2,
        "head_repository": release_train.REPOSITORY,
        "head_branch": "codex/stage3-test",
        "admitted_head": "2" * 40,
        "required_check": "baseline",
        "check_run_id": 44,
        "review_id": 55,
        "review_digest": "3" * 64,
        "admission_id": "stage3-test-a1",
        "admission_sequence": 1,
        "profile": "persistent-lab",
        "adapter": "selectel-systemd/v1",
        "environment": "dcp-wbc-integration-lab-selectel",
        "service": "dcp-wbc-integration-lab",
        "issuer": {
            "actor": "orenvlad-ai",
            "event": "workflow_dispatch",
            "kind": "qualification/v1",
        },
        "qualification_case": "valid",
        "dispatched_at": "2026-08-20T00:00:00+00:00",
    }
    value["manifest_digest"] = release_train.manifest_digest(value)
    return value


class ReleaseTrainTest(unittest.TestCase):
    def test_manifest_digest_excludes_only_its_digest(self) -> None:
        manifest = base_manifest()
        digest = manifest["manifest_digest"]
        self.assertEqual(release_train.manifest_digest(manifest), digest)
        manifest["task_id"] = "changed"
        self.assertNotEqual(release_train.manifest_digest(manifest), digest)

    def test_head_drift_is_one_zero_effect_readmission_fact(self) -> None:
        manifest = base_manifest()
        manifest["qualification_case"] = "head_drift"
        manifest["manifest_digest"] = release_train.manifest_digest(manifest)

        def fake_gh(endpoint: str, *unused: str) -> object:
            if endpoint == f"repos/{release_train.REPOSITORY}":
                return {"id": release_train.REPOSITORY_ID, "visibility": "public"}
            if endpoint.endswith("/pulls/2"):
                return {
                    "state": "open",
                    "draft": False,
                    "base": {"ref": "main"},
                    "head": {
                        "sha": "4" * 40,
                        "repo": {"full_name": release_train.REPOSITORY},
                    },
                }
            if endpoint.endswith("/git/ref/heads/main"):
                return {"object": {"sha": "1" * 40}}
            raise AssertionError(endpoint)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = root / "manifest.json"
            evidence_path = root / "evidence.json"
            output_path = root / "output"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(release_train, "gh", side_effect=fake_gh), mock.patch.dict(
                os.environ,
                {
                    "GITHUB_ACTOR": "orenvlad-ai",
                    "GITHUB_EVENT_NAME": "workflow_dispatch",
                    "GITHUB_REPOSITORY": release_train.REPOSITORY,
                    "GITHUB_RUN_ID": "10",
                    "GITHUB_RUN_ATTEMPT": "1",
                },
                clear=False,
            ):
                with self.assertRaises(SystemExit):
                    release_train.validate(
                        argparse.Namespace(
                            manifest=str(manifest_path),
                            evidence=str(evidence_path),
                            github_output=str(output_path),
                        )
                    )
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(evidence["kind"], "readmission_required")
            self.assertEqual(evidence["reason"], "head_drift")
            self.assertEqual(evidence["effects"]["merges"], 0)
            self.assertEqual(evidence["effects"]["deploys"], 0)
            self.assertEqual(evidence["observed"]["current_head"], "4" * 40)

    def test_wrong_repository_fails_before_provider_reads(self) -> None:
        manifest = base_manifest()
        manifest["qualification_case"] = "wrong_identity"
        manifest["repository"] = "orenvlad-ai/foreign"
        manifest["manifest_digest"] = release_train.manifest_digest(manifest)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = root / "manifest.json"
            evidence_path = root / "evidence.json"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(release_train, "gh") as provider:
                with self.assertRaises(SystemExit):
                    release_train.validate(
                        argparse.Namespace(
                            manifest=str(manifest_path),
                            evidence=str(evidence_path),
                            github_output=str(root / "output"),
                        )
                    )
            provider.assert_not_called()
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(evidence["reason"], "manifest_repository")
            self.assertEqual(evidence["effects"]["ref_updates"], 0)

    def test_missing_prior_proof_is_not_a_replay(self) -> None:
        manifest = base_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = root / "manifest.json"
            output_path = root / "output"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(
                release_train, "gh", return_value={"total_count": 0, "artifacts": []}
            ):
                release_train.replay(
                    argparse.Namespace(
                        manifest=str(manifest_path),
                        output_dir=str(root / "proof"),
                        github_output=str(output_path),
                    )
                )
            self.assertEqual(output_path.read_text(), "replayed=false\n")

    def test_terminal_replay_accepts_github_absolute_path_layout(self) -> None:
        manifest = base_manifest()
        proof = {
            "protocol": "dcp-deployment-proof/v1",
            "admission_digest": manifest["manifest_digest"],
            "merge_sha": "5" * 40,
        }
        proof["proof_digest"] = release_train.proof_digest(proof)

        def fake_download(command: list[str], **unused: object) -> None:
            out_dir = pathlib.Path(command[command.index("--dir") + 1])
            nested = out_dir / "tmp"
            nested.mkdir()
            (nested / "manifest.json").write_text(json.dumps(manifest))
            (nested / "deploy-proof.json").write_text(json.dumps(proof))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest_path = root / "manifest.json"
            output_path = root / "output"
            out_dir = root / "proof"
            manifest_path.write_text(json.dumps(manifest))
            artifact = {
                "expired": False,
                "workflow_run": {"id": 123},
            }
            with mock.patch.object(
                release_train,
                "gh",
                return_value={"total_count": 1, "artifacts": [artifact]},
            ), mock.patch.object(
                release_train.subprocess, "run", side_effect=fake_download
            ):
                release_train.replay(
                    argparse.Namespace(
                        manifest=str(manifest_path),
                        output_dir=str(out_dir),
                        github_output=str(output_path),
                    )
                )
            output = output_path.read_text()
            self.assertIn("replayed=true\n", output)
            self.assertIn(f"proof_digest={proof['proof_digest']}\n", output)
            replay = json.loads((out_dir / "replay-evidence.json").read_text())
            self.assertEqual(replay["effects"]["merges"], 0)
            self.assertEqual(replay["effects"]["deploys"], 0)
            self.assertEqual(replay["effects"]["terminal_proofs_reused"], 1)


if __name__ == "__main__":
    unittest.main()
