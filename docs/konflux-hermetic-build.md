# Hermetic OVMS container inputs

The Dockerfile and rpms.in.yaml select the same 15 production runtime
requests, mapped to the supplied official main-package EVRs. Main packages
such as ovms-gguf-tools and ovms-onnx supply runtime subpackages ovms-libgguf
and ovms-onnx-libs. The main-package list is not a list to install wholesale;
dlpack, development packages, test packages and build tools stay out.

## Base and Python lock

The application base is AIPCC cpu-el9.8:3.6.0, pinned by its index digest in
Dockerfile.konflux. The -source image is not a runnable application base.
Verify the tag's manifest digest with authenticated skopeo before refreshing
the pin, then regenerate both locks against that same pinned base.

```sh
bash scripts/generate-pip-lockfile.sh
```

This is connected preparation on a machine with Podman, Quay authentication
and the pinned image cached. It derives the repository root from its own
location and reads the base from the Dockerfile; no arguments are required.
It runs uv already supplied by that image against the production AIPCC 3.6
CPU wheel index. Hermeto consumes the resulting requirements.txt; it does not
need to execute this Podman helper inside the build task.

Required minimums are pip 26.2.2, uv 0.13.4 when used, and certifi 2026.10.19.
The helper checks pip/uv before connected resolution. requirements.in includes
pip and certifi floors, the generated lock pins their actual versions/hashes,
and the Dockerfile verifies their installed minimums. Keep all transitive
dependencies, even ones supplied by an older base. Do not replace coordinated
native bindings with public PyPI wheels.

## RPM repository discovery and lock generation

The refreshed base inspected on 2026-10-30 contains no .repo files; DNF reports
no repositories available. Base-image context supplies the installed RPM
database, not the missing approved package repository URLs. ovms.repo is a
public template with placeholder endpoints. Copy it outside the checkout and
edit that private copy with the approved binary repository, signing key and
any prefetch authentication. It is a
preparation input and must not be installed in the production image.

If the approved repository is internal, keep its URL/configuration outside
the public checkout. A generated RPM lock also contains resolved download
URLs; review it for internal endpoints before adding it to a public
repository. An internal preparation endpoint does not establish that Konflux
can access it. Final integration needs approved publishable artifact URLs or
a supported private mechanism for supplying both the lock and repository
access to Konflux.

Use rpm-lockfile-prototype in an isolated environment with system DNF/RPM
bindings, skopeo and the required Python tool minimums. The preparation work
used upstream v0.30.1. It accepts local .repo files via contentOrigin.repofiles.
context.containerfile selects the pinned base RPM database; stageNum is
one-based, so this single-stage Dockerfile selects stage 1.

On the VPN-connected machine, use the isolated preparation environment that
contains the resolver and native DNF/RPM bindings. The helper invokes python3
and rpm-lockfile-prototype from PATH; activate that environment first. Skopeo
must have access to the pinned Quay image. No host packages or certificates
are installed by the helper, and no Brew download is needed for this route.

Create a private configuration, then open it in your editor and replace the
placeholders by hand. Only retain enabled repositories with valid endpoints.
This lock is for installing prebuilt runtime RPMs into the image. Its
noSources: true setting skips source-RPM lookup; no source repository is
needed. Remove or disable source-repository sections in older private copies
of the template. Source-package provenance and source distribution remain
separate release workflows.

```sh
mkdir -m 700 -p "$HOME/ovms-private"
cp ovms.repo "$HOME/ovms-private/ovms.repo"
chmod 600 "$HOME/ovms-private/ovms.repo"
```

After editing that file, run from any directory:

```sh
bash /path/to/openvino_model_server/scripts/generate-rpm-lockfile.sh \
    --repo-file "$HOME/ovms-private/ovms.repo" \
    --output-dir "$HOME/ovms-private/lock-output"
```

The helper rejects inputs/output inside the checkout, existing output paths,
enabled placeholder URLs and disabled TLS/signature verification. It creates
a private output directory, snapshots the selected input and Dockerfile, and
resolves x86_64 only against that base with weak dependencies and erasure
disabled. It checks the exact requested EVRs, SHA-256/size metadata, HTTPS
artifact locations and absence of development or QE packages before writing
lock-output/rpms.lock.yaml. It accepts a binary-only lock without corresponding
source-RPM entries. It does not verify downloaded RPM signatures or qualify a
running image; those remain build/qualification requirements.

On failure, read the private lock-output/resolve.log and retain the directory.
Retry with a fresh output path. TLS-chain failures must be resolved using the
VPN machine's approved trust configuration; do not disable sslverify. No
resolver log or generated lock is automatically written into this checkout.
Before sharing either, review it for internal URLs or credentials.

Review a successful lock for unexpected base replacement as well. Do not use
--bare, --local-system or --allowerasing for this layered application image,
and do not substitute prototype RPMs.

The workspace's collect-ovms-brew-info.py can collect build/tag/repository
metadata on a VPN-connected Brew machine when discovery is unavailable here.
Its JSON is not a lockfile and cannot establish access from Konflux itself.

## Konflux and remaining qualification

The component's .tekton files are synchronized from konflux-central. The
prepared RHOAI 3.6 hermetic/prefetch change must reach the authoritative
central branch and then its synchronized component file. This checkout still
lacks that 3.6 file; its inherited ODH/stable and RHOAI 3.5 files do not
constitute the prepared RHOAI 3.6 pipeline. Do not rely on a component-only
Tekton edit surviving synchronization.

The Python lock and matching public inputs can be proposed in a PR now.
The PR remains incomplete for a real build until the RPM lock is generated
and its delivery to Konflux is resolved. If all artifact URLs are approved
for publication, add the reviewed lock as rpms.lock.yaml. If URLs are private,
keep the lock private and arrange an approved mechanism to make it available
before both Hermeto prefetch and Dockerfile assembly. This PR does not yet
implement that private delivery mechanism.

The Dockerfile installs only from the
prefetched local RPM repositories and wheels under /cachi2/output. It does
not have a connected installation fallback. Preserve UID/GID 5000, the normal
/opt/app-root Python prefix and /ovms/bin/ovms entrypoint, without global
LD_LIBRARY_PATH or PYTHONPATH changes.

Final acceptance still requires real prefetch and source/SBOM/signature
checks, image assembly and installed CPU/Python/protocol/MediaPipe testing
with read-only external models. Lock generation does not qualify a new image.

Tool reference: https://github.com/konflux-ci/rpm-lockfile-prototype
