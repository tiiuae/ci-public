#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

echo "Arguments:"
echo "  buildID: '$buildID'"
echo "  resultsPath: '$resultsPath'"
echo "  image: '$image'"
echo "  builderWorkspace: '$builderWorkspace'"

set -x # debug
set -e # exit immediately if a command fails
set -o pipefail # exit if any pipeline command fails

# builderWorkspace should be location of the git repo
# for example
# /home/tc-agent02/Jenkins-agent/workspace/Development/hydra_copy

# if not given, try to use current workspace
[ -z "$builderWorkspace" ] && builderWorkspace=$WORKSPACE

outdir="$(echo "$resultsPath"/"$buildID" | sed 's/ //')"

# run sbomnix for buildtime dependencies
export PATH=$PATH:/nix/var/nix/profiles/default/bin/
nix run github:tiiuae/sbomnix#sbomnix -- "$image" --type=buildtime --depth=1

pwd

# is there a better way to call this script?
python3 ../../hydra_copy/provenance/provenance.py "$outdir"/"$buildID".json \
	--sbom sbom.cdx.json \
    --results-dir "$outdir" \
    --builder-workspace "$builderWorkspace"
