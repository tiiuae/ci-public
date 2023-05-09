#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# This script runs during the container setup.

# We have no sed to easily use template

(
  echo "<runcommand>"
  echo "  job = *:*:*"
  echo "  command = POSTBUILD_SERVER=${1} python3 /setup/postbuild.py"
  echo "</runcommand>"
  echo "max_output_size = 12000000000;"
  echo "base_uri = ${2}"
  echo "using_frontend_proxy = 1"
) > /setup/hydra.conf

# Install python3 that the postbuild.py will need when used
nix-env -i python3

echo "${1}" > /setup/postbuildsrv.txt
