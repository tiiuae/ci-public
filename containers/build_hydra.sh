#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script builds the hydra container

. confs/hydra.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [uid] [gid] [debug=true/false]"
  exit
fi

if [ "$1" != "" ] ; then
  HYDRA_UID="$1"
else
  HYDRA_UID="$(id -u)"
fi
if [ "$2" != "" ] ; then
  HYDRA_GID="$2"
else
  HYDRA_GID="$(id -g)"
fi

if [ "$3" = "true" ] ; then
  CONTAINER_DEBUG="--build-arg CONTAINER_DEBUG=true"
elif [ "$3" = "" ] || [ "$3" = "false" ] ; then
  CONTAINER_DEBUG=""
else
  echo "Unknown debug value \"$3\"!" >&2
  exit 1
fi

if [ "$HC_REMOTE_BUILDERS" != "yes" ] && [ "$HC_REMOTE_BUILDERS" != "no" ] ; then
  echo "Unknown HC_REMOTE_BUILDERS configuration value \"$HC_REMOTE_BUILDERS\"!" >&2
  exit 1
fi

if [ "$HC_SUBSTITUTES" != "yes" ] && [ "$HC_SUBSTITUTES" != "no" ] ; then
  echo "Unknown HC_SUBSTITUTES configuration value \"$HC_SUBSTITUTES\"!" >&2
  exit 1
fi

docker build --build-arg HYDRA_UID="$HYDRA_UID" \
             --build-arg HYDRA_GID="$HYDRA_GID" \
             --build-arg CHANNEL="$HC_CHANNEL" \
             --build-arg HYDRA_REMOTE_BUILDERS="$HC_REMOTE_BUILDERS" \
	     --build-arg HYDRA_SUBSTITUTES="$HC_SUBSTITUTES" \
             --build-arg PB_SRV="$HC_PB_SRV" \
             --build-arg HYDRA_URL="$HYDRA_URL" \
             --build-arg CI_COMMIT_HASH="$(git rev-parse HEAD)" \
             -t "$HC_BASE_LABEL" hydra $CONTAINER_DEBUG -f hydra/Dockerfile
