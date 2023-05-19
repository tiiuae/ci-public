#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Keep this script simple. We don't want THIS to die,
# as then it would remain dead.
while true ; do
  sleep 120
  /setup/extracopy.sh
done
