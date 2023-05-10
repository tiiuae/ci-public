#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script builds the jenkins agent container

. confs/jenkins_agent.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [uid] [gid]"
  exit
fi

if [ "$1" != "" ] ; then
  JAGENT_UID="$1"
else
  JAGENT_UID="$(id -u)"
fi
if [ "$2" != "" ] ; then
  JAGENT_GID="$2"
else
  JAGENT_GID="$(id -g)"
fi

docker build \
       --build-arg JAGENT_UID="$JAGENT_UID" \
       --build-arg JAGENT_GID="$JAGENT_GID" \
       --build-arg CHANNEL="$JAC_CHANNEL" \
       -t "$JAC_BASE_LABEL" jenkins-agent \
       -f jenkins-agent/Dockerfile
