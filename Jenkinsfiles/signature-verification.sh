#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# -------------------------------------------------------------------------
# this script assumes that tiiuae/scs-pki-research has been cloned into the
# working directory[1], and is on a branch where signer container can be found,
# and that yubikey has been provisioned on the machine
#
# [1] ~/Jenkins-agent/workspace/{env}/Supply_chain_security/signature_verification/
# -------------------------------------------------------------------------

# file and signature given should be nix store paths that are either
# found locally or can be downloaded from cache.vedenemo.dev
echo "Arguments:"
echo "  file: '$file'"
echo "  signature: '$signature'"

set -x # debug

# use nix profile
export PATH=$PATH:/nix/var/nix/profiles/default/bin/

# copy the file and it's signature from the binary cache if they don't exist locally
COPY="nix copy --from https://cache.vedenemo.dev"
[[ ! -f "$file" ]] && $COPY "$file"
[[ ! -f "$signature" ]] && $COPY "$signature"

# get the sha256 of the file being verified
FILE_HASH="$(sha256sum "$file" | awk '{print $1}')"

# get the signature, which for some reason includes dos line breaks
SIGNATURE_CONTENT="$(cat "$signature" | dos2unix)"

# verify the file using given signature
# grep -q exits with code 1 if it doesn't find a match, failing the job
scs-pki-research/yubikey/start.sh --verify \
	--h=$FILE_HASH \
    --sg=$SIGNATURE_CONTENT \
    | grep -q "Signature is valid"
