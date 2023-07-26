#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# inputs
IMAGE=$1
BUILDINFO=$2
OUTPUT_DIR=$3
OUTPUT_FILENAME=$4

BUILD_ID="$(jq -r '.build' "$BUILDINFO")"
OUT="$OUTPUT_DIR/$OUTPUT_FILENAME"

cd "$OUTPUT_DIR" || exit

# generate buildtime sbom (and suppress noisy stdout)
sbomnix "$IMAGE" --type=buildtime --depth=1 > /dev/null 2>&1

# generate the provenance file
python3 /setup/provenance.py "$BUILDINFO" \
    --out "$OUT" \
    --sbom sbom.cdx.json \
    --ci-version "$(cat /setup/ci-version)"

# clean up sbom files
# they are no longer needed
rm sbom*

# add provenance to nix store
PROVENANCE="$(nix-store --add "$OUT")"

# sign the provenance file and upload both files to binary cache
SIGNATURE="$(/setup/sign.sh "$PROVENANCE")"
/setup/upload.sh "$PROVENANCE" "$SIGNATURE" > /dev/null 2>&1

echo "PROVENANCE_LINK=\"$PROVENANCE\""
echo "PROVENANCE_SIGNATURE=\"$SIGNATURE\""
