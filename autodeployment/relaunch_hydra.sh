#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Relaunch hydra from scratch

AUTODEPLOY_DIR="$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)"

cd "$(dirname "$0")/../containers" || exit 1

. confs/hydra.default

if [ "$HC_NONINTERACTIVE" != "on" ] ; then
  echo "This setup has not been configured for non-interactive relaunch" >&2
  exit 1
fi

# Stop and clear out old container if needed
docker stop "${HC_BASE_LABEL}-cnt" 2>/dev/null || /usr/bin/env true
docker container rm "${HC_BASE_LABEL}-cnt" 2>/dev/null || /usr/bin/env true

if [ -n "$HC_STORE_PATH" ] && [ -d "$HC_STORE_PATH" ] ; then
  chmod -R u+w "$HC_STORE_PATH"
  if ! rm -Rf "$HC_STORE_PATH" ; then
    echo "Failed to delete old store!" >&2
    exit 1
  fi
fi

./build_hydra.sh

# Initial setup run
./run_hydra.sh

# Setup configuration files to store/
if ! "${AUTODEPLOY_DIR}/copy_hydra_confs.sh" "$(pwd)/confs/hydra/" "$HC_STORE_PATH" ; then
  echo "Failed to setup conf files!" >&2
  exit 1
fi

if [ -x "confs/hydra/autodeploy_hook" ] ; then
  # Fragment to run parallel with hydra startup
  (
    # Wait for hydra to start up
    sleep 40
    ./confs/hydra/autodeploy_hook
  ) &
fi

# Actual run
./run_hydra.sh
