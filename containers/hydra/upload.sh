#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Callback script called after a package has been built

# Exit on error
set -e

BINCACHECONF="/home/hydra/confs/binarycache.conf"

if [ -r  "$BINCACHECONF" ]; then
    # shellcheck disable=SC1090 # Shut up about not being able to follow
    . "$BINCACHECONF"

    if [ -r "$CACHE_SSH_KEY_FILE" ]; then
        if [ -n "$CACHE_SERVER" ]; then
            CACHE_PORT="${CACHE_PORT:-22}"
            export NIX_SSHOPTS="-i$CACHE_SSH_KEY_FILE -p$CACHE_PORT"

            nix-copy-closure --to "$CACHE_SERVER" "$@"
        fi
    else
        echo "${CACHE_SSH_KEY_FILE} is nonexisting or unreadable" >&2
        exit 1
    fi
fi
