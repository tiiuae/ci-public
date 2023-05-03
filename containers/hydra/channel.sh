#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script runs during the container setup.

if [ "$1" != "" ] ; then
  # We have to get hydra from nixos-22.05, to avoid
  # https://github.com/NixOS/nix/issues/6981
  nix-channel --add https://nixos.org/channels/nixos-${1}-small nixos-${1}
fi

nix-channel --update
