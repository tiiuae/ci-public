#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Run the binarycache docker container

# bash needed for '-s' and 'n' parameters for 'read'

. confs/bcache.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [cache=./cache]"
  exit
fi

if [ "$1" != "" ] ; then
  BCACHE="$1"
else
  BCACHE="./cache"
fi

if ! [ -d "$BCACHE" ] ; then
  echo "\"$BCACHE\" does not exist. Do you want it created now? (y/n)"
  echo -n "> "
  read -n 1 ANSWER
  echo
  if [ "$ANSWER" != "y" ] ; then
    echo "Aborted!" >&2
    exit 1
  fi
fi

if ! [ -d "${BCACHE}" ] ; then
  if ! mkdir -p "${BCACHE}/nix" ||
     ! mkdir -p "${BCACHE}/home" ; then
    echo "Failed to create \"$BCACHE\"" >&2
    exit 1
  fi

  # Make sure we have absolute path
  BCACHE="$(cd "${BCACHE}" || exit 1 ; pwd)"

  echo "Copying store"
  # Mount store as /nix/outside, so the container can copy files between internal store and outside store
  docker run -i -p ${HC_PORT}:3000 --mount type=bind,source="${BCACHE}/nix",target=/nix/outside --mount type=bind,source="${BCACHE}/home",target=/nix/outside_home -e SETUP_RUN=1 -t "$BCC_BASE_LABEL"
else
  # Make sure we have absolute path
  BCACHE="$(cd "${BCACHE}" || exit 1 ; pwd)"
fi

MOUNTS="\
 --mount type=bind,source=${BCACHE}/nix,target=/nix \
 --mount type=bind,source=${BCACHE}/home,target=/home/hydra \
"

docker run -i -p ${BCC_SSH_PORT}:22 \
         $MOUNTS \
         -t "$BCC_BASE_LABEL"
