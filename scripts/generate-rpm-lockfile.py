#!/usr/bin/env python3
"""Resolve the pinned image's RPM additions using private VPN inputs/output."""

import argparse
import configparser
from importlib.metadata import version
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def outside_checkout(path):
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(REPO_ROOT):
        raise ValueError(
            "Private repository inputs and output must be outside the checkout"
        )
    return resolved


def check_repositories(path):
    config = configparser.ConfigParser(interpolation=None)
    with path.open() as stream:
        config.read_file(stream)
    enabled = [
        section
        for section in config.values()
        if section.name != config.default_section
        and section.getboolean("enabled", True)
    ]
    if not enabled:
        raise ValueError("No enabled repositories in the private .repo file")
    for section in enabled:
        for option in ("baseurl", "metalink", "mirrorlist"):
            value = section.get(option, "")
            if "example.invalid" in value or "REPLACE-ME" in value:
                raise ValueError(
                    "Replace enabled repository placeholders in the private .repo file"
                )
        if not section.getboolean("gpgcheck", True) or not section.getboolean(
            "sslverify", True
        ):
            raise ValueError("Keep RPM signatures and TLS verification enabled")


def validate_lock(lock, requested):
    arches = lock.get("arches", [])
    if len(arches) != 1 or arches[0].get("arch") != "x86_64":
        raise ValueError("Expected only the x86_64 lock architecture")
    arch = arches[0]
    if arch.get("module_metadata"):
        raise ValueError("Unexpected module metadata requires review")
    packages, sources = arch.get("packages", []), arch.get("source", [])
    for item in packages + sources:
        if urlsplit(item["url"]).scheme != "https":
            raise ValueError("Expected HTTPS artifact URLs")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", item.get("checksum", "")):
            raise ValueError("Expected SHA-256 artifact checksums")
        if not isinstance(item.get("size"), int) or item["size"] <= 0:
            raise ValueError("Missing artifact size")
    source_names = {Path(unquote(urlsplit(item["url"]).path)).name for item in sources}
    missing = {item.get("sourcerpm") for item in packages} - source_names
    if missing:
        raise ValueError(
            "Missing matching source RPMs; supply source repository coverage: "
            + repr(sorted(str(name) for name in missing))
        )
    selected = {item["name"]: item["evr"].removeprefix("0:") for item in packages}
    for nvr in requested:
        name, ver, release = nvr.rsplit("-", 2)
        if selected.get(name) != ver + "-" + release:
            raise ValueError("Requested exact runtime EVR absent from lock: " + nvr)
    if any(
        name.endswith(("-devel", "-tests", "-debuginfo", "-debugsource"))
        for name in selected
    ):
        raise ValueError("Unexpected development or QE package in runtime closure")


def resolve(output, repo_file):
    inputs = output / "inputs"
    inputs.mkdir()
    shutil.copyfile(REPO_ROOT / "Dockerfile.konflux", inputs / "Dockerfile.konflux")
    shutil.copyfile(repo_file, inputs / "ovms.repo")
    config = yaml.safe_load((REPO_ROOT / "rpms.in.yaml").read_text())
    config["contentOrigin"] = {"repofiles": [str(inputs / "ovms.repo")]}
    config["arches"] = ["x86_64"]
    config["installWeakDeps"] = False
    config["allowerasing"] = False
    source = inputs / "rpms.in.yaml"
    source.write_text(yaml.safe_dump(config, sort_keys=False))
    draft = output / "rpms.resolved.yaml"
    command = [
        "rpm-lockfile-prototype",
        "--arch",
        "x86_64",
        "--outfile",
        str(draft),
        str(source),
    ]
    print(
        "Resolving against the pinned AIPCC base; private log:",
        output / "resolve.log",
        flush=True,
    )
    with (output / "resolve.log").open("w") as log:
        result = subprocess.run(
            command, cwd=inputs, stdout=log, stderr=subprocess.STDOUT
        )
    if result.returncode:
        raise ValueError(
            "Resolver failed; inspect private resolve.log (TLS, access or dependency error)"
        )
    validate_lock(yaml.safe_load(draft.read_text()), config["packages"])
    shutil.copyfile(draft, output / "rpms.lock.yaml")
    print("Validated private lock:", output / "rpms.lock.yaml")
    print(
        "Review URLs before publication. This helper does not make the lock available to Konflux."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-file",
        type=Path,
        required=True,
        help="Private .repo file outside the checkout; edit URLs there by hand",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New private directory outside the checkout; existing paths are refused",
    )
    args = parser.parse_args()
    try:
        repo_file, output = outside_checkout(args.repo_file), outside_checkout(
            args.output_dir
        )
        check_repositories(repo_file)
        if output.exists():
            raise ValueError(
                "Output already exists; preserve it and choose a new directory"
            )
        for command in ("rpm-lockfile-prototype", "skopeo"):
            if not shutil.which(command):
                raise ValueError("Missing preparation tool: " + command)
        # The same isolated environment should supply Python and the resolver.
        from pip._vendor.packaging.version import Version

        for name, floor in (("pip", "26.2.2"), ("certifi", "2026.10.19")):
            if Version(version(name)) < Version(floor):
                raise ValueError(
                    name + " must be >= " + floor + " in the preparation environment"
                )
        os.umask(0o077)
        output.mkdir(mode=0o700, parents=True)
        resolve(output, repo_file)
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
