#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0


# Callback script called after a package has been built

if [ -f /home/hydra/confs/binarycache.conf ] && [ -f /home/hydra/.ssh/bcache.key ] ; then
  . /home/hydra/confs/binarycache.conf
  if [ -n "$CACHE_SERVER" ] ; then
    if [ -n "$CACHE_PORT" ] ; then
      export NIX_SSHOPTS="-i /home/hydra/.ssh/bcache.key -p $CACHE_PORT"
    else
      export NIX_SSHOPTS="-i /home/hydra/.ssh/bcache.key"
    fi

    nix-copy-closure --to hydra@$CACHE_SERVER $OUT_PATHS $DRV_PATH
  fi
fi
