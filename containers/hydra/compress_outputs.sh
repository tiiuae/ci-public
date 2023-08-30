#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Make a package for web server of the outputs

# Exit on error
set -e

PREFIX="POSTBUILD_PACKAGE"
SIGNSCRIPT="/setup/sign.sh"
WEBUPLOAD="/home/hydra/toupload"
TEMP_DIR="/home/hydra/temp"

PREREQUISITES=("mktemp --version" "jq --help" "tar --version" "xz --version" "basename --version")

# Check given prerequisites (given commands can be executed)
function Check_prerequisites {
    local notfound=0

    while [ -n "$1" ]; do
        echo "Testing $1"
        if ! $1 > /dev/null 2>&1; then
            echo "Error: ${1% *} not found in path!" >&2
            notfound=1
        fi
        shift
    done

    if [ $notfound -eq 1 ]; then
        exit 1
    fi
}

case "$1" in
"")
    : # Pass
;;
--help)
    echo "Usage: $0"
    echo "       $0 [--help|--check-script|--prerequisites]"
    echo ""
    echo "          --help = Show this help message"
    echo "  --check-script = Run shellcheck and bashate on the script itself"
    echo " --prerequisites = Check for commands required to run the script"
    echo ""
    exit 0
;;
--check-script)
    # This not intended to be used inside the container
    # Just to check for errors on development environment that has shellcheck and bashate installed
    if shellcheck --help > /dev/null 2>&1 && bashate --help > /dev/null 2>&1; then
        if shellcheck "$0" && bashate -i E006 "$0"; then
            echo "Nothing to complain"
        fi
    else
        echo "Please install shellcheck and bashate to use check-script functionality"
    fi
    exit 0
;;
--prerequisites)
    # Check that commands are available
    Check_prerequisites "${PREREQUISITES[@]}"
    echo "All commands seem to work" >&2
    exit 0
;;
*)
    echo "Invalid parameter: $1" >&2
    exit 1
;;
esac

if [ -z "$HYDRA_JSON" ]; then
    echo "HYDRA_JSON was not defined" >&2
    exit 1
fi

# Get hydra server name
HYDRA="$(<"/setup/postbuildsrv.txt")"

# Create temp dir
mkdir -p "$TEMP_DIR"
TMPDIR="$(mktemp -p "$TEMP_DIR" -d)"

# Remove temp dir contents on exit
trap 'rm -rf "$TMPDIR"' EXIT

NUM_OUTPUTS="$(jq ".outputs | length" "$HYDRA_JSON")"
BUILD="$(jq -r ".build" "$HYDRA_JSON")"
JOB="$(jq -r ".job" "$HYDRA_JSON")"

mkdir -p "${WEBUPLOAD}/${JOB}"

# Get name of the first output
BASENAME="$(jq -r ".outputs[0].path" "$HYDRA_JSON")"
[ "$BASENAME" = "null" ] && { echo "No outputs found" >&2; exit 1; }
# Remove /nix/store/ from start of path
BASENAME="${BASENAME##/nix/store/}"
# Add hydra name and build number to name
BASENAME+="-${HYDRA}-${BUILD}"

# Add tempdir and and add extension
PACKAGE="${TMPDIR}/${BASENAME}.tar"

for (( i=0; i < NUM_OUTPUTS; i++ )); do
    OUTPUT="$(jq -r ".outputs[$i].path" "$HYDRA_JSON")"
    # Add output to the package
    tar rf "$PACKAGE" -C /nix/store "${OUTPUT##/nix/store/}"
    echo "${PREFIX}_OUTPUT[${i}]=\"${OUTPUT}\""

    # Sign the output
    SIGNATURE_FILE="$($SIGNSCRIPT "$OUTPUT")"
    # If signing was not configured SIGNATURE_FILE is empty
    if [ -n "$SIGNATURE_FILE" ]; then
        # Add signature to package
        tar rf "$PACKAGE" -C /nix/store "${SIGNATURE_FILE##/nix/store/}"
        echo "${PREFIX}_OUTPUT_SIGNATURE[${i}]=\"${SIGNATURE_FILE}\""
    fi
done

xz -z -0 "$PACKAGE"
mv -f "${PACKAGE}.xz" "${WEBUPLOAD}/${JOB}/"

echo "${PREFIX}=\"${JOB}/${BASENAME}.tar.xz\""
