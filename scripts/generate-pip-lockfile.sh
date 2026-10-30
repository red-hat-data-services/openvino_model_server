#!/bin/bash
# Generate requirements.txt from requirements.in.
# Runs pip-compile inside the target base image to ensure correct
# Python version, platform, and no CUDA deps are pulled in.
#
# torch is only available as a pre-built Linux wheel on the AIPCC public index,
# not on standard PyPI. pip-compile uses the AIPCC index so torch resolves
# correctly. The --index-url is kept in requirements.txt so Hermeto uses the
# same index during prefetch — no netrc or allow_binary needed since the index
# is public and the wheels are Red Hat-built.
#
# When to run this script manually:
#   - Base image changes (pip-compile must run inside the container to resolve
#     the correct platform and pre-installed packages; MintMaker cannot do this)
#   - Adding a new package to requirements.in
#
# When NOT needed (MintMaker handles it automatically):
#   - openvino version bumps: MintMaker's pip-compile manager detects the change
#     in requirements.in and regenerates requirements.txt in the same MR.
#
# Usage: scripts/generate-pip-lockfile.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_IMAGE=$(awk '$1 == "FROM" { print $2; exit }' "${REPO_ROOT}/Dockerfile.konflux")
AIPCC_INDEX=${AIPCC_INDEX:-https://packages.redhat.com/api/pypi/public-rhai/rhoai/3.6/cpu-ubi9/simple/}
if [[ ${BASE_IMAGE} != *@sha256:* ]]; then
    echo 'Dockerfile.konflux must select a literal digest-pinned base image.' >&2
    exit 2
fi

echo "Resolving requirements.in with the x86_64 Python 3.12 base: ${BASE_IMAGE}"
echo "Using index: ${AIPCC_INDEX}"

podman run --rm --pull=never --platform linux/amd64 --user 0 \
    --workdir /work -v "${REPO_ROOT}:/work:z" \
    -e AIPCC_INDEX="${AIPCC_INDEX}" -e UV_CACHE_DIR=/tmp/uv-cache \
    --entrypoint /bin/bash "${BASE_IMAGE}" -euc '
# Check the network-facing preparation tools before resolving dependencies.
python3.12 - <<"PY"
from importlib.metadata import version
from pip._vendor.packaging.version import Version
import subprocess

assert Version(version("pip")) >= Version("26.2.2"), "pip must be >= 26.2.2"
uv_version = subprocess.check_output(["uv", "--version"], text=True).split()[1]
assert Version(uv_version) >= Version("0.13.4"), "uv must be >= 0.13.4"
PY
uv pip compile requirements.in \
    --config-file /dev/null \
    --default-index "${AIPCC_INDEX}" --emit-index-url \
    --python /opt/app-root/bin/python3.12 \
    --python-platform x86_64-manylinux_2_34 \
    --no-python-downloads --only-binary=:all: \
    --generate-hashes --upgrade \
    --custom-compile-command scripts/generate-pip-lockfile.sh \
    --output-file requirements.txt
'
