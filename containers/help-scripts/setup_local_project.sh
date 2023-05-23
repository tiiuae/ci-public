#!/bin/bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Setup project that uses ghaf clone seen as /srv/ghaf inside the container.
# Set HC_SRV_MOUNT in hydra.local configuration file so that /srv gets mounted
# to the parent directory of the ghaf repository on the host.

. confs/hydra.default

export HYDRACTL_USERNAME="automation"
export HYDRACTL_PASSWORD="${PW_AUTO}"

python3 ../hydractl/hydractl.py http://localhost:${HC_PORT}/ AP -p local -D local

python3 ../hydractl/hydractl.py \
        http://localhost:${HC_PORT}/ AJ \
        -p local -j local -D local \
        -t flake -f git+file:/srv/ghaf/
