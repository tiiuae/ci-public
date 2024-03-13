#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Setup hydra projects

# Support user defined HYDRACTL
if [ "$HYDRACTL" = "" ] ; then
  HYDRACTL="../hydractl/hydractl.py"
fi

if ! [ -f "$HYDRACTL" ] ; then
  echo "There is no hydractl \"$HYDRACTL\"" >&2
  exit 1
fi

if [ "$1" != "" ] ; then
  EXT_PORT="$1"
else
  EXT_PORT=3000
fi

SERVER="http://localhost:${EXT_PORT}/"
export HYDRACTL_USERNAME="automation"

# TODO: All this should come from a configuration layer, and not be
#       hardcoded guesses of what is wanted

# ghaf
python3 "$HYDRACTL" "$SERVER" AP -p ghaf -D ghaf

python3 "$HYDRACTL" \
        "$SERVER" AJ \
        -p ghaf -j ghaf -D ghaf \
        -t flake -f git+https://github.com/tiiuae/ghaf/

# FMO
python3 "$HYDRACTL" "$SERVER" AP -p fmo -D FMO

python3 "$HYDRACTL" \
        "$SERVER" AJ \
        -p fmo -j fmo -D FMO \
        -t flake -f git+https://github.com/tiiuae/FMO-OS/?branch=target_for_public_build
