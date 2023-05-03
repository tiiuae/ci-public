#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Normal container run - not the first run that does setup work instead.

pg_ctl start -D /home/hydra/db

# GC_DONT_GC is needed for hydra-evaluator to work around
# https://github.com/NixOS/hydra/issues/1186
export LOGNAME="hydra"
export HYDRA_DATA="/home/hydra/db"
export HYDRA_CONFIG="/setup/hydra.conf"
hydra-server &
GC_DONT_GC="true" hydra-evaluator &
hydra-notify &
hydra-queue-runner

pg_ctl stop -D /home/hydra/db
