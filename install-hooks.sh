#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

set -e

if [ ! -d ./.git/hooks ]; then
    echo "./.git/hooks not found" >&2
    exit 1
fi

if [ ! -f ./githooks/check-commit.sh ]; then
    echo "./githooks/check-commit.sh not found" >&2
    exit 1
fi

if [ "$1" == "--uninstall" ]; then
    if [ ! -e ./.git/hooks/commit-msg ]; then
        echo "./.git/hooks/commit-msg does not exist"
        exit 1
    else
        rm -f ./.git/hooks/commit-msg
        echo "Check commit hook removed"
    fi
else
    if [ -e ./.git/hooks/commit-msg ]; then
        echo "./.git/hooks/commit-msg exists already" >&2
        exit 1
    fi

    ln -s ../../githooks/check-commit.sh ./.git/hooks/commit-msg
    echo "Check commit hook installed"
fi
