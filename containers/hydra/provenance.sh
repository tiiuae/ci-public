#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

set -x

IMAGE=$1
BUILDINFO=$2
BUILD_ID=$(jq -r '.build' "$BUILDINFO")
OUTPUT_DIR="/home/hydra/results/$BUILD_ID"

echo "PROVENANCE FOR BUILD $BUILD_ID"

# create output dir in hydra home
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR" || exit

# generate buildtime sbom
sbomnix "$IMAGE" --type=buildtime --depth=1

# generate the provenance file
python3 /setup/provenance.py "$BUILDINFO" \
	--output-dir "$OUTPUT_DIR" \
	--sbom sbom.cdx.json

# clean up sbom files
# they are no longer needed
rm sbom*
