#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0


# Callback script called after a package has been built

if [ -f /home/hydra/upload_ip.txt ] && [ -f /home/hydra/.ssh/key ] ; then
  if [ -f /home/hydra/upload_port.txt ] ; then
    export NIX_SSHOPTS="-i /home/hydra/.ssh/key -p $(cat /home/hydra/upload_port.txt)"
  else
    export NIX_SSHOPTS="-i /home/hydra/.ssh/key"
  fi

  nix-copy-closure --to hydra@$(cat /home/hydra/upload_ip.txt) $OUT_PATHS $DRV_PATH
fi
