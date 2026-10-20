#!/bin/bash
# Connected preparation only. Requires rpm-lockfile-prototype and Podman;
# neither belongs in the production image.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if grep -Eq '^[[:space:]]*(baseurl|metalink|mirrorlist)[[:space:]]*=.*(example[.]invalid|REPLACE-ME)' \
    "${REPO_ROOT}/ovms.repo"; then
    echo 'STRAWMAN: replace the binary/source URLs in ovms.repo and confirm the signing key first.' >&2
    echo 'No RPM lockfile has been generated; see docs/konflux-hermetic-build.md.' >&2
    exit 2
fi
if ! command -v rpm-lockfile-prototype >/dev/null; then
    echo 'Install rpm-lockfile-prototype in your preparation environment, not in the image.' >&2
    exit 2
fi
cd "${REPO_ROOT}"
rpm-lockfile-prototype --outfile=rpms.lock.yaml rpms.in.yaml
