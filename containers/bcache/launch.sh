#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container entry point

if [ "$SETUP_RUN" = "1" ] ; then
  ssh-keygen -A
  # Copy internal store content to the outside store on first run
  cp -R /nix/store /nix/outside/
  cp -R /nix/var /nix/outside/
  cp -R /nix/etc /nix/outside/
  chown -R hydra:nixbld /nix/outside/store
  chown -R hydra:nixbld /nix/outside/var
  cp -R /home/hydra/.ssh /nix/outside_home
  chown -R hydra:hydra /nix/outside_home
  chmod -R go-w /nix/outside_home
else
  ./run.sh
fi
