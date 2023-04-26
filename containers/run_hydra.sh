#!/bin/bash

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

# Run the hydra docker container

# bash needed for '-s' and 'n' parameters for 'read'

. confs/hydra.default

PRIVILEGED="--privileged"

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [store root=./store] [/srv mount=not in use] [debug mode=false]"
  exit
fi

if [ "$1" != "" ] ; then
  STORE="$1"
else
  STORE="./store"
fi

SRV="$2"

if [ "$3" = "true" ] ; then
  CONTAINER_DEBUG="true"
elif [ "$3" = "" ] || [ "$3" = "false" ] ; then
  CONTAINER_DEBUG="false"
else
  echo "Unknown debug value \"$3\"!" >&2
  exit 1
fi

if ! [ -d "$STORE" ] ; then
  echo "\"$STORE\" does not exist. Do you want it created now? (y/n)"
  echo -n "> "
  read -n 1 ANSWER
  echo
  if [ "$ANSWER" != "y" ] ; then
    echo "Aborted!" >&2
    exit 1
  fi
fi

if ! [ -f "${STORE}/populated" ] ; then
  if [ -f "${STORE}/initializing" ] ; then
    echo "\"${STORE}\" is partly populated by earlier run." >&2
    echo "Don't know how to fix." >&2
    exit 1
  fi
  # First run.
  echo "First run - setting things up"
  echo

  if [ "$PW_ADMIN" = "" ] ; then
    echo "Give hydra admin password"
    echo -n "> "
    read -s PW_ADMIN
    echo
    echo "Confirm hydra admin password"
    echo -n "> "
    read -s PW_CONFIRM
    echo
    if [ "$PW_ADMIN" != "$PW_CONFIRM" ] ; then
      echo "Passwords do not match. Aborting!" >&2
      exit 1
    fi
  fi

  if [ "$PW_AUTO" = "" ] ; then
    echo "Give hydra automation password"
    echo -n "> "
    read -s PW_AUTO
    echo
    echo "Confirm hydra automation password"
    echo -n "> "
    read -s PW_CONFIRM
    echo
    if [ "$PW_AUTO" != "$PW_CONFIRM" ] ; then
      echo "Passwords do not match. Aborting!" >&2
      exit 1
    fi
  fi

  if ! mkdir -p "${STORE}/nix" ||
     ! mkdir -p "${STORE}/home"
  then
    echo "Failed to create store directory \"${STORE}\"" >&2
    exit 1
  fi
  touch "${STORE}/initializing"
  # Make sure we have absolute path
  STORE="$(cd "${STORE}" || exit 1 ; pwd)"

  echo "Copying store"
  # Mount store as /nix/outside, so the container can copy files between internal store and outside store
  docker run -i -p ${HC_PORT}:3000 \
       $PRIVILEGED \
       --mount type=bind,source="${STORE}/nix",target=/nix/outside \
       --mount type=bind,source="${STORE}/home",target=/nix/outside_home \
       -e SETUP_RUN=1 $CONTAINER_DEBUG_ARG -t "$HC_BASE_LABEL"

  # Mount store over the nix store, run rest of the setup
  mkdir -p "${STORE}/home"
  echo "Restarting container, running setup"
  docker run -i -p ${HC_PORT}:3000 \
       $PRIVILEGED \
       --mount type=bind,source="${STORE}/nix",target=/nix \
       --mount type=bind,source="${STORE}/home",target=/home/hydra \
       -e SETUP_RUN=2 -e PW_ADMIN="$PW_ADMIN" -e PW_AUTO="$PW_AUTO" \
       -t "$HC_BASE_LABEL"
  echo "Restarting container, configuring hydra projects and jobsets"
  docker run --name "${HC_BASE_LABEL}-configure" -p ${HC_PORT}:3000 \
       $PRIVILEGED \
       --mount type=bind,source="${STORE}/nix",target=/nix \
       --mount type=bind,source="${STORE}/home",target=/home/hydra \
       -t "$HC_BASE_LABEL" &
  sleep 15
  if ! HYDRACTL_PASSWORD="$PW_AUTO" ./hydra/hydra-configure.sh "${HC_PORT}" ; then
    docker stop "${HC_BASE_LABEL}-configure"
    docker container rm "${HC_BASE_LABEL}-configure"
    echo "Hydra project setup failed" >&2
    exit 1
  fi
  docker stop "${HC_BASE_LABEL}-configure"
  docker container rm "${HC_BASE_LABEL}-configure"
  touch "${STORE}/populated"
  rm "${STORE}/initializing"
  echo
  echo "Setup ready. Use ./run_hydra again for regular run."
  exit
else
  # Make sure we have absolute path
  STORE="$(cd "${STORE}" || exit 1 ; pwd)"
fi

MOUNTS="\
 --mount type=bind,source=${STORE}/nix,target=/nix \
 --mount type=bind,source=${STORE}/home,target=/home/hydra \
"

if [ "$SRV" != "" ] ; then
  MOUNTS="$MOUNTS --mount type=bind,source=${SRV},target=/srv"
fi

echo "MOUNTS:" $MOUNTS

if [ "$CONTAINER_DEBUG" = "true" ] ; then
  # Debug run
  docker run -i -p ${HC_PORT}:3000 \
	 $PRIVILEGED \
	 $MOUNTS \
	 -e SETUP_RUN="ext" \
         -t "$HC_BASE_LABEL"
else
  # Regular run
  docker run -i -p ${HC_PORT}:3000 \
	 $PRIVILEGED \
         $MOUNTS \
         -t "$HC_BASE_LABEL"
fi
