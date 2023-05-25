#!/bin/bash
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# An example script demonstrating usage of hydractl in scripts.
# Please do not interface this script in other scripts, but use hydractl
# directly instead.

# Stop on any error
set -e

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Adds a project and jobset for building given repo branch to hydra."
    echo "It's assumed that hydractl.py is in the current directory and credentials have"
    echo "been set up properly in the environment variables or in credentials.txt."
    echo ""
    echo "Usage: ${0} URL REPO BRANCH [PREFIX] [INTERVAL]"
    echo ""
    echo "       URL = URL to hydra"
    echo "      REPO = Repo to be built by hydra"
    echo "    BRANCH = Repo branch"
    echo "    PREFIX = Prefix added to hydra project and jobset identifiers (default \"\")"
    echo "  INTERVAL = Poll interval in seconds (default 3600)"
    echo ""
    echo "Example:"
    echo "  ${0} https://hydra2.vedenemo.dev/ https://github.com/tiiuae/ghaf ghaf-23.05 ghaf- 0"
    echo ""
    exit 1
fi

URL="${1%%/}/"
REPO="${2%%/}"
BRANCH="$3"

if [ -z "$4" ]; then
    PREFIX=""
else
    PREFIX="$4"
fi

if [ -z "$5" ]; then
    INTERVAL=3600
else
    INTERVAL="$5"
fi

HCTL="python3 hydractl.py $URL"

# Replace periods with dashes in ID (It won't be valid for hydra otherwise)
# There might be other required conversions, add them here if encountered
ID="${BRANCH//./-}"

# Make sure ID starts with the prefix.
ID="${PREFIX}${ID##$PREFIX}"

# Add project
$HCTL AP \
    --project "$ID" \
    --display "$BRANCH" \
    --description "Project for ${REPO} ${BRANCH}" \
    --homepage "${REPO}/tree/${BRANCH}"
# Add jobset
$HCTL AJ \
    --project "$ID" \
    --jobset "$ID" \
    --description "Jobset for ${REPO} ${BRANCH}" \
    --check "$INTERVAL" \
    --type flake \
    --flake "git+${REPO}?ref=${BRANCH}"
