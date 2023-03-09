#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

# Normal container run - not the first run that does setup work instead.

pg_ctl start -D /home/hydra/db

# GC_DONT_GC is needed for hydra-evaluator to work around
# https://github.com/NixOS/hydra/issues/1186
export LOGNAME="hydra"
export HYDRA_DATA="/home/hydra/db"
export HYDRA_CONF="/setup/hydra.conf"
hydra-server &
GC_DONT_GC="true" hydra-evaluator &
hydra-queue-runner

pg_ctl stop -D /home/hydra/db
