#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

COMMIT_HASH=3916a93e0bb694215a86b3b251bfa02344dc40d1

git clone https://github.com/tiiuae/sbomnix
cd sbomnix || exit
git checkout "$COMMIT_HASH"

env NIX_PROFILE=/nix/var/nix/profiles/default nix-env -f default.nix --install
