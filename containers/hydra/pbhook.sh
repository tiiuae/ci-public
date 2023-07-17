#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Callback script called after a package has been built

SIGNATURES=$(/setup/sign.sh $OUT_PATHS $DRV_PATH)
/setup/upload.sh $OUT_PATHS $DRV_PATH $SIGNATURES
