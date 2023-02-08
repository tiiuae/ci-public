#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

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
python3 "$HYDRACTL" "$SERVER" AP -i ghaf -D ghaf

python3 "$HYDRACTL" \
        "$SERVER" AJ \
        -p ghaf -i ghaf -D ghaf \
        -t flake -f git+https://github.com/tiiuae/ghaf/
