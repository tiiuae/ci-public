#!/bin/bash
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Stop on error
set -e

HCTL="python3 hydractl.py https://hydra2.vedenemo.dev/"
GHAF="https://github.com/tiiuae/ghaf"

if [ -n "$1"  ]; then
    BRANCH="$1"
    # Replace periods with dashes in ID (It won't be valid for hydra otherwise)
    ID="${BRANCH//./-}"
    # Make sure ID starts with 'ghaf-' but have it only once if branch name already starts with it
    ID="ghaf-${ID##ghaf-}"
    # Add project
    $HCTL AP \
        --project "$ID" \
        --display "$BRANCH" \
        --description "Ghaf project ${BRANCH}" \
        --homepage "${GHAF}/tree/${BRANCH}"
    # Add jobset
    $HCTL AJ \
        --project "$ID" \
        --jobset "$ID" \
        --description "Ghaf project ${BRANCH}" \
        --check 3600 \
        --type flake \
        --flake "git+${GHAF}?ref=${BRANCH}"
else
    echo "Adds a project and jobset for building given Ghaf branch to hydra2."
    echo "It's assumed that hydractl.py is in the current directory and hydra2"
    echo "credentials have been set up properly in the environment variables or"
    echo "in credentials.txt."
    echo ""
    echo "Usage: ${0} BRANCH"
    echo ""
    echo "  BRANCH = Ghaf branch e.g. 'ghaf-23.05'"
    echo ""
    exit 1
fi
