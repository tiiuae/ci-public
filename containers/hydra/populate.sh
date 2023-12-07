#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script runs during the setup runs of the container

# This works around a problem that hydra cannot "build" (fetch)
# some initial source packages before it has been bootstrapped
# Here we pre-populate the store with those required packages.
mkdir -p /home/hydra/packages/nix/store
cat /setup/packages.lst |
    ( while read PACKAGE DISCARD_REST
      do
	if [ "$PACKAGE" != "" ] && [ "$PACKAGE" != "#" ] ; then
          nix-env -i "$PACKAGE"
          nix-store --add-root /home/hydra/packages${PACKAGE} --indirect --realise "$PACKAGE"
	fi
      done )
