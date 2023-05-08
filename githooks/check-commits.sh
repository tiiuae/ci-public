#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Get actual directory of this bash script
SDIR="$(dirname "${BASH_SOURCE[0]}")"
SDIR="$(realpath "$SDIR")"

TMPF="/tmp/TEMP.MSG"

function On_exit {
    rm -f "$TMPF"
}

trap On_exit EXIT

function Check_commit {
    git log -1 --pretty=format:%B "$1" > "$TMPF"

    echo "${1} ---------"
    cat "$TMPF"
    echo "--------------------------------------------------"
    if "${SDIR}/check-commit.sh" --noninteractive "$TMPF"; then
        return 0
    else
        return 1
    fi
}

if [ -z "$GITHUB_CONTEXT" ]; then
    echo "GITHUB_CONTEXT is not set"
    exit 7
fi

RET=0
for SHA in $(jq -r .event.commits[].id <<< "$GITHUB_CONTEXT"); do
    Check_commit "$SHA"
    RET=$(($RET | $?))
done

case $RET in
3|2)
    echo "::error title=ERROR::There are errors in the commit message(s)"
;;
1)
    echo "::warning title=WARNING::There are warnings about the commit message(s)"
;;
0)
    echo "::notice title=Success::Commit message(s) approved"
;;
esac

exit $RET
