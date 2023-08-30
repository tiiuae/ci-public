#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Keep this script simple. We don't want THIS to die,
# as then it would remain dead.
sleep 10
while true; do
    # Starting in background is fine, the scripts have locks.
    /setup/webupload.sh &
    sleep 60
    /setup/cachecopy.sh &
    sleep 60
done
