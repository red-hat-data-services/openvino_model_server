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
BASE_IMAGE=$(grep '^BASE_IMAGE=' "${REPO_ROOT}/build-args/ubi9.conf" | cut -d= -f2)

# AIPCC public index — contains torch pre-built Linux wheels (built by fondue).
# Use the test distribution until the prod distribution for 3.6-EA2 is published.
AIPCC_INDEX="https://packages.redhat.com/api/pypi/public-rhai/rhoai/3.6-EA2/cpu-ubi9-test/simple/"

echo "Generating requirements.txt inside: ${BASE_IMAGE}"
echo "Using index: ${AIPCC_INDEX}"

podman run --rm \
    --platform linux/amd64 \
    --user 0 \
    -v "${REPO_ROOT}:/work:z" \
    -e AIPCC_INDEX="${AIPCC_INDEX}" \
    --interactive \
    "${BASE_IMAGE}" \
    bash << 'CONTAINERSCRIPT'

set -euo pipefail
cd /work

pip install pip-tools --index-url https://pypi.org/simple/ -q

pip-compile requirements.in \
    --index-url "${AIPCC_INDEX}" \
    --allow-unsafe \
    --upgrade \
    --generate-hashes \
    --output-file requirements.txt

# Strip pip options that Hermeto does not support.
# sympy/networkx/mpmath are pure-Python torch deps pre-installed in the base image.
# Keep --index-url: Hermeto reads it to know where to fetch packages during prefetch.
grep -v \
    -e "^--extra-index-url" \
    -e "^--only-binary" \
    -e "^--prefer-binary" \
    -e "^sympy==" \
    -e "^networkx==" \
    -e "^mpmath==" \
    requirements.txt > requirements.txt.tmp && mv requirements.txt.tmp requirements.txt

# Flatten multi-line hash entries to single lines — Hermeto requires
# --hash options on the same line as the package requirement.
python3 - << 'PYEOF'
import re
with open("requirements.txt") as f:
    lines = f.readlines()
output = []
for line in lines:
    stripped = line.rstrip("\n")
    if re.match(r"^\s+#", stripped):
        continue
    if re.match(r"^\s+--hash=", stripped):
        if output:
            hashes = re.findall(r"--hash=\S+", stripped)
            prev = re.sub(r"\s*\\\s*$", "", output[-1].rstrip("\n"))
            output[-1] = prev + " " + " ".join(hashes) + "\n"
        continue
    output.append(line)
with open("requirements.txt", "w") as f:
    f.writelines(output)
print("Flattened", len(output), "entries")
PYEOF

echo "Done: requirements.txt updated"
CONTAINERSCRIPT
