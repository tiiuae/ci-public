#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script builds the binarycache container

. confs/bcache.default

if [ "$1" = "-h" ] || [ "$1" = "--help" ] ; then
  echo "Usage: $0"
  exit
fi

docker build -t "$BCC_BASE_LABEL" bcache -f bcache/Dockerfile
