#!/bin/bash
# Connected preparation only. Requires rpm-lockfile-prototype and Skopeo;
# neither belongs in the production image.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${RPM_LOCK_PYTHON:-python3}" "${REPO_ROOT}/scripts/generate-rpm-lockfile.py" "$@"
