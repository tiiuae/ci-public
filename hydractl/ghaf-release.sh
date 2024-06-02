#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2024 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

PRDIR="$(pwd)"

# Correct relative path for hydra.default to function correctly
cd ../containers && . confs/hydra.default
cd "${PRDIR}"

export HYDRACTL_USERNAME="automation"
export HYDRACTL_PASSWORD="${PW_AUTO}"

HYDRA_URL="http://localhost:${HC_PORT}"

if [ -z "$1" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
    echo
    echo "Usage: ${0} [REPO] [RELEASE NUMBER, e.g. \"24.06\"]"
    echo "E.g. ${0} github:tiiuae/ghaf 24.06"
    echo
    exit 1
fi

HCTL="python3 hydractl.py ${HYDRA_URL}"
REPO="$1"
REL="$2"
TAG="ghaf-${REL}"

# Replace periods with dashes in ID (It won't be valid for hydra otherwise)
# There might be other required conversions, add them here if encountered
ID="${REL//./-}"

# Add project
${HCTL} AP \
	--project "ghaf-${ID}" \
	--display "ghaf-${REL}" \
	--description "Project for ${REPO} release ${REL}" \
	--homepage "${REPO}/tree/${TAG}"

# Add jobset
${HCTL} AJ \
	--project "ghaf-${ID}" \
	--jobset "ghaf-${ID}" \
	--description "Jobset for ${REPO} release ${REL}" \
	--type flake \
	--flake "${REPO}/${TAG}"
