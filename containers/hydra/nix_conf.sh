#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie

# This script runs during the container setup.

# $1 - key
# $2 - value
function nix_conf_line() {
  if grep "$1[ =]" nix.conf > /dev/null ; then
    sed "s/$1[ =].*/$1 = $2/" nix.conf > nix.conf.new
    mv nix.conf.new nix.conf
  else
    echo "$1 = $2" >> nix.conf
  fi
}

cd /setup/

cp /etc/nix/nix.conf nix.conf

nix_conf_line "cores" "4"
nix_conf_line "max-jobs" "16"
nix_conf_line "builders" ""
nix_conf_line "allowed-uris" "https://github.com/ https://source.codeaurora.org/"
nix_conf_line "post-build-hook" "/setup/upload.sh"
nix_conf_line "system-features" "nixos-test benchmark big-parallel kvm"
nix_conf_line "experimental-features" "nix-command flakes"

CONFFILE=$(nix-store --add nix.conf)

rm /etc/nix/nix.conf
ln -s $CONFFILE /etc/nix/nix.conf
