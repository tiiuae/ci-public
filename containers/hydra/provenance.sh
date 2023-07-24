#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# inputs
IMAGE=$1
BUILDINFO=$2
OUTPUT_DIR=$3
OUTPUT_FILENAME=$4

BUILD_ID=$(jq -r '.build' "$BUILDINFO")

echo "PROVENANCE FOR BUILD $BUILD_ID"

cd "$OUTPUT_DIR" || exit

# generate buildtime sbom
sbomnix "$IMAGE" --type=buildtime --depth=1

# generate the provenance file
python3 /setup/provenance.py "$BUILDINFO" \
    --out "$OUTPUT_DIR/$OUTPUT_FILENAME" \
    --sbom sbom.cdx.json \
    --ci-version "$(cat /setup/ci-version)"

# clean up sbom files
# they are no longer needed
rm sbom*
