"""Offline checks for private input/output handling and lock acceptance."""

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "generate-rpm-lockfile.py"
SPEC = importlib.util.spec_from_file_location("rpm_lock_helper", SCRIPT)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def fixture_lock():
    # Labelled synthetic metadata only; no real lock or acquisition is made.
    binary = dict(
        name="sample",
        evr="1-2",
        sourcerpm="sample-1-2.src.rpm",
        url="https://example.invalid/sample-1-2.x86_64.rpm",
        checksum="sha256:" + "a" * 64,
        size=10,
    )
    return dict(arches=[dict(arch="x86_64", packages=[binary], source=[])])


class PrivateLockTests(unittest.TestCase):
    def test_checkout_paths_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            alias = Path(temp) / "checkout-link"
            alias.symlink_to(HELPER.REPO_ROOT, target_is_directory=True)
            for path in (HELPER.REPO_ROOT / "private.repo", alias / "lock-output"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    HELPER.outside_checkout(path)
            self.assertEqual(HELPER.outside_checkout(Path(temp)), Path(temp).resolve())

    def test_placeholders_and_verification_bypasses_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "private.repo"
            for value in (
                "baseurl=https://example.invalid/REPLACE-ME/",
                "baseurl=https://example.com/\nsslverify=0",
                "baseurl=https://example.com/\ngpgcheck=0",
            ):
                with self.subTest(value=value):
                    repo.write_text("[binary]\nenabled=1\n" + value + "\n")
                    with self.assertRaises(ValueError):
                        HELPER.check_repositories(repo)
            repo.write_text("[binary]\nbaseurl=https://example.com/\ngpgcheck=1\n")
            HELPER.check_repositories(repo)

    def test_valid_lock_and_epoch_zero(self):
        lock = fixture_lock()
        HELPER.validate_lock(lock, ["sample-1-2"])
        lock["arches"][0]["packages"][0]["evr"] = "0:1-2"
        HELPER.validate_lock(lock, ["sample-1-2"])

    def test_incomplete_or_wrong_lock_is_rejected(self):
        for case in (
            "unexpected_source",
            "wrong_evr",
            "wrong_arch",
            "bad_checksum",
            "file_url",
            "qe",
        ):
            lock = fixture_lock()
            arch = lock["arches"][0]
            package = arch["packages"][0]
            if case == "unexpected_source":
                arch["source"] = [
                    dict(url="https://example.invalid/sample-1-2.src.rpm")
                ]
            elif case == "wrong_evr":
                package["evr"] = "1-3"
            elif case == "wrong_arch":
                arch["arch"] = "aarch64"
            elif case == "bad_checksum":
                package["checksum"] = "sha256:unknown"
            elif case == "file_url":
                package["url"] = "file:///private/sample.rpm"
            else:
                extra = copy.deepcopy(package)
                extra["name"] = "sample-tests"
                arch["packages"].append(extra)
            with self.subTest(case=case), self.assertRaises(ValueError):
                HELPER.validate_lock(lock, ["sample-1-2"])

    def test_binary_only_resolution_and_wrong_evr_finalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout, output = root / "checkout", root / "private-output"
            checkout.mkdir()
            output.mkdir()
            (checkout / "Dockerfile.konflux").write_text(
                "FROM example.invalid/base@sha256:" + "c" * 64 + "\n"
            )
            (checkout / "rpms.in.yaml").write_text(
                yaml.safe_dump(dict(packages=["sample-1-2"]))
            )
            repo = root / "private.repo"
            repo.write_text("[binary]\nbaseurl=https://example.com/\n")

            lock = fixture_lock()

            def resolve_without_sources(command, **kwargs):
                config = yaml.safe_load(Path(command[-1]).read_text())
                self.assertIs(config["noSources"], True)
                Path(command[command.index("--outfile") + 1]).write_text(
                    yaml.safe_dump(lock)
                )
                return type("Result", (), {"returncode": 0})()

            with patch.object(HELPER, "REPO_ROOT", checkout), patch.object(
                HELPER.subprocess, "run", side_effect=resolve_without_sources
            ):
                HELPER.resolve(output, repo)
                self.assertTrue((output / "rpms.lock.yaml").exists())
                # A missing source is allowed, but an incorrect binary EVR
                # must still prevent finalizing the lock.
                lock["arches"][0]["packages"][0]["evr"] = "1-3"
                failed_output = root / "failed-output"
                failed_output.mkdir()
                with self.assertRaisesRegex(ValueError, "exact runtime EVR absent"):
                    HELPER.resolve(failed_output, repo)
            self.assertFalse((failed_output / "rpms.lock.yaml").exists())
            self.assertTrue((failed_output / "rpms.resolved.yaml").exists())
            self.assertFalse((checkout / "rpms.lock.yaml").exists())


if __name__ == "__main__":
    unittest.main()
