#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

set -x

# inputs
IMAGE=$1
BUILDINFO=$2
OUTPUT_DIR=$3

BUILD_ID=$(jq -r '.build' "$BUILDINFO")

echo "PROVENANCE FOR BUILD $BUILD_ID"

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
