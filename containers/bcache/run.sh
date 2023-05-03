#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Normal container run - not the first run that does setup work instead.

/root/.nix-profile/bin/sshd &

nix-serve
