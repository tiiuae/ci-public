#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Run the Jenkins controller docker container

. confs/jenkins_controller.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [persistent store=./jcontrol]"
  exit
fi

if [ "$1" != "" ] ; then
  JCCACHE="$1"
else
  JCCACHE="./jcontrol"
fi

if ! [ -d "$JCCACHE" ] ; then
  echo "\"$JCCACHE\" does not exist. Do you want it created now? (y/n)"
  echo -n "> "
  read -n 1 ANSWER
  echo
  if [ "$ANSWER" != "y" ] ; then
    echo "Aborted!" >&2
    exit 1
  fi
fi

if ! [ -d "${JCCACHE}" ] ; then
  if ! mkdir -p "${JCCACHE}/nix" ; then
    echo "Failed to create \"$JCCACHE\"" >&2
    exit 1
  fi

  # Make sure we have absolute path
  JCCACHE="$(cd "${JCCACHE}" || exit 1 ; pwd)"

  if ! ( cd "${JCCACHE}" || exit 1
    git clone -n --depth=1 --filter=tree:0 \
      https://github.com/tiiuae/ci-public home
    cd home || exit 1
    git sparse-checkout set --no-cone jenkins
    git checkout
  ) ; then
    echo "Failed to setup Jenkins config clone" >&2
    exit 1
  fi
else
  # Make sure we have absolute path
  JCCACHE="$(cd "${JCCACHE}" || exit 1 ; pwd)"
fi

MOUNTS="\
 --mount type=bind,source=${JCCACHE}/nix,target=/nix \
 --mount type=bind,source=${JCCACHE}/home/jenkins,target=/jenkins \
"

# Regular run
docker run -i -p ${JCC_PORT}:8080 \
           $MOUNTS \
           -t "$JCC_BASE_LABEL"
