#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script runs during the container setup.

# $1 - key
# $2 - value
function nix_conf_line() {
  if grep "$1[ =]" nix.conf > /dev/null ; then
    # We have no 'sed', so use grep to remove old line entirely
    grep -v "$1[ =]" nix.conf > nix.conf.new
    mv nix.conf.new nix.conf
  fi
  echo "$1 = $2" >> nix.conf
}

cd /setup/

cp /etc/nix/nix.conf nix.conf

# As the actual max number simultaneous tasks is cores * max-jobs,
# Set "cores" lower than actual number of cores
declare -i SET_CORES
SET_CORES=$(nproc)/4
nix_conf_line "cores" "${SET_CORES}"
nix_conf_line "max-jobs" "16"

if [ "$1" = "no" ] ; then
  nix_conf_line "builders" ""
else
  ln -s /home/hydra/confs/machines /etc/nix/
fi

nix_conf_line "allowed-uris" "https://github.com/ https://source.codeaurora.org/"
nix_conf_line "post-build-hook" "/setup/pbhook.sh"
nix_conf_line "system-features" "nixos-test benchmark big-parallel kvm"
nix_conf_line "experimental-features" "nix-command flakes"

# This requires --privileged container.
nix_conf_line "sandbox" "true"

CONFFILE=$(nix-store --add nix.conf)

rm /etc/nix/nix.conf
ln -s "$CONFFILE" /etc/nix/nix.conf
