#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

# This script runs during the setup runs of the container

# This works around a problem that hydra cannot "build" (fetch)
# some initial source packages before it has been bootstrapped
# Here we pre-populate the store with those required packages.
cat /setup/packages.lst |
    ( while read PACKAGE DISCARD_REST
      do
	if [ "$PACKAGE" != "" ] && [ "$PACKAGE" != "#" ] ; then
          nix-env -i "$PACKAGE"
	fi
      done )
