#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

# Setup postgresql for hydra to use

mkdir -p /home/hydra/db
chmod go-rwx /home/hydra/db

initdb -D /home/hydra/db
pg_ctl start -D /home/hydra/db
createdb
