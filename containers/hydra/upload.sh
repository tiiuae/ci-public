#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0


# Callback script called after a package has been built

if [ -f /home/hydra/confs/binarycache.conf ] ; then
  . /home/hydra/confs/binarycache.conf
  if [ -f "$CACHE_SSH_KEY_FILE" ] ; then
    if [ -n "$CACHE_SERVER" ] ; then
      if [ -n "$CACHE_PORT" ] ; then
        export NIX_SSHOPTS="-i $CACHE_SSH_KEY_FILE -p $CACHE_PORT"
      else
        export NIX_SSHOPTS="-i $CACHE_SSH_KEY_FILE"
      fi

      nix-copy-closure --to $CACHE_SERVER $OUT_PATHS $DRV_PATH
    fi
  fi
fi
