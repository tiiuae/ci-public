#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

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

docker build --build-arg HYDRA_UID="$HYDRA_UID" --build-arg HYDRA_GID="$HYDRA_GID" \
       -t "$HC_BASE_LABEL" hydra $CONTAINER_DEBUG -f hydra/Dockerfile
