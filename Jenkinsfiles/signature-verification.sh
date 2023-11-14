#!/bin/bash
# shellcheck disable=SC2154

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# -------------------------------------------------------------------------
# this script assumes that sha256tree.py is copied from ci-public repo
# to this working directory and that needed <hydra>.pem file is there also.
# $pem_file is Jenkins parameter and this script is used as it is on Jenkins job
# warning about that is ignored in second line
# -------------------------------------------------------------------------

# Calculate sha256 for a file or a directory
function Calc_sha256sum {
    python3 sha256tree.py --plain -- "$1"
}

# Function to clear temp
function On_exit {
    if [ -n "$MYTEMP" ]; then
        cd /
        # Remove read-only attributes so files can be removed
        chmod -R u+w "$MYTEMP"
        rm -rf "$MYTEMP"
    fi
}

# Run function on exit
trap On_exit EXIT

if [ "$1" == "--check-script" ]; then
    # (Note that official nix path_to_check will never be --check-script)
    # This just to check for errors on development environment that has shellcheck and bashate installed
    if shellcheck --help > /dev/null 2>&1 && bashate --help > /dev/null 2>&1; then
        if shellcheck "$0" && bashate -i E006 "$0"; then
            echo "Nothing to complain"
        fi
    else
        echo "Please install shellcheck and bashate to use check-script functionality"
    fi
    exit 1
fi

[ -z "$path_to_check" ] && { echo "Path not given" >&2; exit 1; }
[ -z "$signature_file" ] && { echo "Signature file not given" >&2; exit 1; }

# path_to_check and signature_file given should be nix store paths that are either
# found locally or can be downloaded from cache.vedenemo.dev
echo "Arguments:"
echo "  path_to_check: '$path_to_check'"
echo "  signature_file: '$signature_file'"

# Stop on any error
set -e

set -x # debug

# use nix profile
export PATH=$PATH:/nix/var/nix/profiles/default/bin/

# copy the file and it's signature_file from the binary cache if they don't exist locally
COPY="nix copy --from https://cache.vedenemo.dev"
[[ ! -e "$path_to_check" ]] && $COPY "$path_to_check"
[[ ! -f "$signature_file" ]] && $COPY "$signature_file"

# get the sha256 of the file being verified
PATH_HASH="$(Calc_sha256sum "$path_to_check")"

# Check for valid input as xxd -r will silently ignore errors
if [[ ! $PATH_HASH =~ ^[0-9A-Fa-f]{64}$ ]]; then
    echo "${PATH_HASH}: Hash calculation failed" >&2
    exit 1
fi

# Make temp directory and copy <hydra>.pem file there
MYTEMP=$(mktemp -d)
cp "$pem_file" /"$MYTEMP"
cd "${MYTEMP}"

# store hash to a file
echo "$PATH_HASH" > digest.hex

# convert the hashfile into binary format
xxd -r -p digest.hex digest.bin

# convert signature file to signature.bin file
openssl enc -base64 -d -in "$signature_file" -out signature.bin

# validate the authenticity of the signature
if ! openssl dgst -sha256 -verify "$pem_file" -signature signature.bin digest.bin > /dev/null 2>&1; then
	  echo "Signature check failed" >&2
    exit 1
else
    echo "Signature check ok" >&2
fi
