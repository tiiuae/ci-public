#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

COMMIT_HASH=9df4fb380b94fce54c4374958e7fc69a573cf6ec

git clone https://github.com/tiiuae/sbomnix
cd sbomnix || exit
git checkout "$COMMIT_HASH"

env NIX_PROFILE=/nix/var/nix/profiles/default nix-env -f default.nix --install
