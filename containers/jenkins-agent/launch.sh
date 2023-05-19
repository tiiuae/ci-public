#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container entry point

if [ "$SETUP_RUN" = "1" ] ; then
  # Copy internal store content to the outside store on first run
  cp -R /nix/store /outside/nix/
  cp -R /nix/var /outside/nix/
  cp -R /nix/etc /outside/nix/
  cp -R /jenkins/.ssh /outside/jenkins/
  chown -R jenkins:jenkins /outside/jenkins/
  chmod -R go-w /outside

elif [ "$SETUP_RUN" = "2" ] ; then
  ssh-keygen -A
else
  ./run.sh
fi
