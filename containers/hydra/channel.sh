#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script runs during the container setup.

# Remove initial default channel
nix-channel --remove nixpkgs

if [ "$1" != "" ] ; then
  nix-channel --add "https://nixos.org/channels/nixos-${1}"
else
  DEFCHANNEL="23.11"
  nix-channel --add "https://nixos.org/channels/nixos-${DEFCHANNEL}"
fi

# Rinstate nixpkgs, to get hydra
nix-channel --add "https://nixos.org/channels/nixpkgs-unstable"

nix-channel --update
