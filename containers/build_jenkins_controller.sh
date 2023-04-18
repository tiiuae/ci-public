#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script builds the jenkins controller container

. confs/jenkins_controller.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0 [uid] [gid]"
  exit
fi

if [ "$1" != "" ] ; then
  JCONTROL_UID="$1"
else
  JCONTROL_UID="$(id -u)"
fi
if [ "$2" != "" ] ; then
  JCONTROL_GID="$2"
else
  JCONTROL_GID="$(id -g)"
fi

docker build \
             --build-arg JCONTROL_UID="$JCONTROL_UID" \
             --build-arg JCONTROL_GID="$JCONTROL_GID" \
             -t "$JCC_BASE_LABEL" jenkins-controller \
	     -f jenkins-controller/Dockerfile
