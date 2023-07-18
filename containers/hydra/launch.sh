#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container entry point

if [ "$SETUP_RUN" = "1" ] ; then
  # Copy internal store content to the outside store on first run
  cp -R /nix/store /nix/outside/
  cp -R /nix/var /nix/outside
  chown -R :nixbld /nix/outside/store
  cp -R /home/hydra/* /nix/outside_home/
  cp /setup/postbuild.py /nix/outside_home/
  cp /setup/messager.py /nix/outside_home/
  chmod u+x /nix/outside_home/messager.py
elif [ "$SETUP_RUN" = "2" ] ; then
  # Run rest of the setup scripts
  /setup/postgres.sh
  /setup/hydra.sh
  /setup/populate.sh
elif [ "$SETUP_RUN" = "ext" ] ; then
  if ! [ -f /etc/container-debug-true ] ; then
    echo "This is not a debug version of the container" >&2
    exit 1
  fi
  /nix/var/nix/external_script
else
  # On later runs, outside store has been mounted over internal store.
  # Run as 'hydra'
  ./run.sh
fi
