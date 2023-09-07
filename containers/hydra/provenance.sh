#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# get the build id from buildinfo
BUILD_ID="$(jq -r '.build' "$HYDRA_JSON")"

# allow overriding suffix with env variable
SUFFIX="${POSTBUILD_PROVENANCE_SUFFIX:--provenance.json}"

# provenance filename structure
PROVENANCE_FILENAME="${POSTBUILD_SERVER}-${BUILD_ID}${SUFFIX}"

# get path to the build output
OUTPUT_PATH="$(jq -r '.outputs | .[0] | .path' "$HYDRA_JSON")"

# location to save the provenance file and sboms in
TMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TMP_DIR"' EXIT
cd "$TMP_DIR" || exit 1
SAVE_AS="${TMP_DIR}/${PROVENANCE_FILENAME}"

# generate buildtime sbom (and suppress noisy stdout)
sbomnix "$OUTPUT_PATH" --type=buildtime --depth=1 > /dev/null 2>&1

# tell shellcheck to ignore that this file doesn't exist
# (file is generated in run_hydra.sh)
# shellcheck source=/dev/null
. "${HOME}/setup_config"

# generate the provenance file
/setup/provenance.py "$HYDRA_JSON" \
    --out "$SAVE_AS" \
    --sbom sbom.cdx.json \
    --ci-version "$(cat /setup/ci-version)" \
    --hydra-url "http://localhost:3000"

if [ ! -f "$PROVENANCE_FILENAME" ]; then
    echo "${PROVENANCE_FILENAME} was not generated" && exit 1
fi

# add provenance to nix store
PROVENANCE="$(nix-store --add "$SAVE_AS")"
/setup/upload.sh "$PROVENANCE"

# create signature for the provenance file
SIGNATURE="$(/setup/sign.sh "$PROVENANCE")"
if [ ! -f "$SIGNATURE" ]; then
    echo "Signature creation failed!"
else
    /setup/upload.sh "$SIGNATURE"
fi

echo "PROVENANCE_FILE=\"${PROVENANCE}\""
echo "PROVENANCE_SIGNATURE=\"${SIGNATURE}\""
