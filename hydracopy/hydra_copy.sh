#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Ville-Pekka Juntunen <ville-pekka.juntunen@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# ------------------------------------------------------------------------
# This script is used as "action" of hydrascraper.py and it will copy given Hydra build nix store from http://binarycache.vedenemo.dev
# And it add Hydra build ID to working list if copy succeeded
# ------------------------------------------------------------------------

set -e

echo "Hydra Build ID: $HYDRA_BUILD_ID"
echo "Hydra store path:  $HYDRA_OUTPUT_STORE_PATHS"
nix copy --from http://binarycache.vedenemo.dev $HYDRA_OUTPUT_STORE_PATHS
nix copy --derivation --from http://binarycache.vedenemo.dev `nix-store --query --deriver $HYDRA_OUTPUT_STORE_PATHS`
echo "Add build ID and store path to working list"
echo "$HYDRA_BUILD_ID:$HYDRA_OUTPUT_STORE_PATHS" >> wlist.txt
