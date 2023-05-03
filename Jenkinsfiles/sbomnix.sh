#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

check_file_exists () {
    if ! [ -s "$1" ]; then
        echo "Error: File not found: \"$1\"" >&2
        exit 1
    fi
}

strip_ansi_colors () {
    sed -e 's/\x1b\[[0-9;]*m//g'
}

echo "Arguments:"
echo "  image: '$image'"
echo "  buildID: '$buildID'"
echo "  resultsPath: '$resultsPath'"

export PATH=$PATH:/nix/var/nix/profiles/default/bin/

set -x # debug
set -e # exit immediately if a command fails
set -u # treat unset variables as an error and exit
set -o pipefail # exit if any pipeline command fails
pwd
outdir="$(echo "$resultsPath"/"$buildID"/ | sed 's/ //')"
check_file_exists "$image"
check_file_exists "$outdir"

printf '\n\n---\nGenerate meta.json\n---\n'
nix-env -qa --meta --json '.*' >meta.json
check_file_exists meta.json

printf '\n\n---\nRun sbomnix (runtime dependencies)\n---\n'
nix run github:tiiuae/sbomnix#sbomnix -- "$image" --meta=meta.json --type=runtime |& strip_ansi_colors
cp sbom.csv "$outdir/sbom.runtime__$buildID.csv"
cp sbom.cdx.json "$outdir/sbom.runtime__$buildID.cdx.json"
cp sbom.spdx.json "$outdir/sbom.runtime__$buildID.spdx.json"

printf '\n\n---\nRun vulnxscan (runtime dependencies)\n---\n'
nix run github:tiiuae/sbomnix#vulnxscan -- "$image" |& strip_ansi_colors
cp vulns.csv "$outdir/vulns.runtime__$buildID.csv"
