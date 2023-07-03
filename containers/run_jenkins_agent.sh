#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Run the Jenkins agent docker container

. confs/jenkins_agent.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [persistent store=./jagent]"
  exit
fi

if [ "$1" != "" ] ; then
  JACACHE="$1"
else
  JACACHE="./jagent"
fi

if ! [ -d "$JACACHE" ] ; then
  echo "\"$JACACHE\" does not exist. Do you want it created now? (y/n)"
  echo -n "> "
  read -r -n 1 ANSWER
  echo
  if [ "$ANSWER" != "y" ] ; then
    echo "Aborted!" >&2
    exit 1
  fi
fi

if ! [ -d "${JACACHE}" ] ; then
  if ! mkdir -p "${JACACHE}/nix" ||
     ! mkdir -p "${JACACHE}/jenkins" ; then
    echo "Failed to create \"${JACACHE}\"" >&2
    exit 1
  fi

  # Make sure we have absolute path
  JACACHE="$(cd "${JACACHE}" || exit 1 ; pwd)"

  echo "Copying store"
  # Mount store as /outside, so the container can copy files between internal store and outside store
  docker run -i --mount type=bind,source="${JACACHE}",target=/outside \
	 -e SETUP_RUN=1 -t "$JAC_BASE_LABEL"

  # Mount store over the nix store, run rest of the setup
  echo "Restarting container, running setup"
  docker run -i \
       --mount type=bind,source="${JACACHE}/nix",target=/nix \
       --mount type=bind,source="${JACACHE}/jenkins",target=/jenkins \
       -e SETUP_RUN=2 \
       -t "$JAC_BASE_LABEL"

  echo
  echo "Setup ready. Use ./run_jenkins_agent.sh again for regular run."
  exit

else
  # Make sure we have absolute path
  JACACHE="$(cd "${JACACHE}" || exit 1 ; pwd)"
fi

MOUNTS="\
 --mount type=bind,source=${JACACHE}/nix,target=/nix \
 --mount type=bind,source=${JACACHE}/jenkins,target=/jenkins \
"

# Regular run
docker run -i -p "${JAC_SSH_PORT}:22" \
           $MOUNTS \
           -t "$JAC_BASE_LABEL"
