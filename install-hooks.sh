#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

set -e

if [ ! -d ./.git/hooks ]; then
    echo "./.git/hooks not found" >&2
    exit 1
fi

if [ ! -f ./githooks/check-commit.sh ]; then
    echo "./githooks/check-commit.sh not found" >&2
    exit 1
fi

if [ -e ./.git/hooks/commit-msg ]; then
    echo "./.git/hooks/commit-msg exists already" >&2
    exit 1
fi

ln -s ../../githooks/check-commit.sh ./.git/hooks/commit-msg
