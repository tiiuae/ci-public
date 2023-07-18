#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Callback script called after a package has been built

/home/hydra/scripts/sign.sh $OUT_PATHS $DRV_PATH
/home/hydra/scripts/upload.sh $OUT_PATHS $DRV_PATH
