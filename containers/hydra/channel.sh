#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

# This script runs during the container setup.

if [ "$1" = "22.05" ] ; then
  # We have to get hydra from nixos-22.05, to avoid
  # https://github.com/NixOS/nix/issues/6981
  nix-channel --add https://nixos.org/channels/nixos-22.05-small nixos-22.05
fi

nix-channel --update
