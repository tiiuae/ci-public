#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Copy hydra configuration files to its store

if [ -d "$1/confs" ] ; then
  if ! cp -R "$1/confs" "$2/home/" ; then
    echo "Failed to copy hydra confs" >&2
    exit 1
  fi
fi

if [ -d "$1/.ssh" ] ; then
  if ! cp -R "$1/.ssh" "$2/home/" ; then
    echo "Failed to copy hydra ssh confs" >&2
    exit 1
  fi
fi
