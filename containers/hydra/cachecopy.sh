#!/root/.nix-profile/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Copies signature files to cache

# Exit on error
set -e

# Remove lock file on exit
function On_exit {
    rm -f "$EC_LOCK"
}

# Truncates a file from start, in place. Useful e.g. for capping log files
# $1 = Name of file to truncate
# $2 = How many lines to keep in file
function Truncate_from_start {
    local file linestokeep linestoremove bytestoremove lines

    file="${1:?}"
    linestokeep="${2:?}"
    lines="$(wc -l < "$file")"

    # Only do this if there are more lines in the file than we'd like to keep
    if [ "$lines" -gt "$linestokeep" ]; then
        linestoremove="$((lines-linestokeep))"
        # Get removed lines size in bytes
        bytestoremove="$(head -n "$linestoremove" "$file" | wc -c)"
        # Move contents inside the file, in place
        dd if="$file" bs="$bytestoremove" skip=1 conv=notrunc,fsync of="$file" 2> /dev/null
        # Remove extra bytes
        truncate -s "-$bytestoremove" "$file"
    fi
}


# This is intended for debugging the script outside hydra container
# pkill is not available inside the hydra containter atm
if [ -n "$EC_DEBUG" ]; then
    echo ""
    echo "Press CTRL-C to single step"
    echo "Kill from another window to abort"
    echo ""
    echo "To see the outputs from the logged part of script,"
    echo "you'll have to e.g. tail -f the log file in another window"
    echo ""
    set -x
    trap "pkill -f 'sleep 1.123h'" INT
    trap "set +xe; sleep 1.123h; set -xe" DEBUG
fi

# Allow overriding any of the config variables
EC_WRITEDIR="${EC_WRITEDIR-"/home/hydra/extracopy"}"
EC_LOCK="${EC_LOCK-"/tmp/extracopy.lock"}"
EC_LOG="${EC_LOG-"${EC_WRITEDIR}/extracopy.log"}"
EC_INCACHE="${EC_INCACHE-"${EC_WRITEDIR}/extracopy.incache"}"
EC_NEWCACHE="${EC_NEWCACHE-"${EC_WRITEDIR}/extracopy.newfiles.cache"}"
EC_CACHECONFFIL="${EC_CACHECONFFIL-"/home/hydra/confs/binarycache.conf"}"
EC_THISSRVFIL="${EC_THISSRVFIL-"/setup/postbuildsrv.txt"}"


case "$1" in
"")
    : # Pass
;;
check-script)
    # This not intended to be used inside the hydra container
    # Just to check for errors on development environment that has shellcheck and bashate installed
    if shellcheck --help > /dev/null 2>&1 && bashate --help > /dev/null 2>&1; then
        if shellcheck "$0" && bashate -i E006 "$0"; then
            echo "Nothing to complain"
        fi
    else
        echo "Please install shellcheck and bashate to use check-script functionality"
    fi
    exit 1
;;
*)
    echo "Script for copying images and build info files to cache and web server"
    echo "This script is expected to be run periodically from e.g. cron"
    echo ""
    echo "Usage: ${0} [check-script]"
    echo ""
    echo "  check-script = Run shellcheck and bashate on the script itself"
    echo ""
    exit 1
;;
esac

# This is not meant to be thread safe locking, just enough to not start another copy process from cron
# if earlier one is still running

# If already running, just exit
if [ -f "$EC_LOCK" ]; then
    exit 0
fi

# Run On_exit function on exit
trap On_exit EXIT

# Create lock file
touch "$EC_LOCK"

# Create dir for logs
mkdir -p "$EC_WRITEDIR"

# stdout and stderr are redirected to log file in following block
{
    if [ -r "$EC_CACHECONFFIL" ] ; then
        date "+%d.%m.%4Y %H:%M:%S ------------------------------------"
        date "+%H:%M:%S Sourcing $EC_CACHECONFFIL"
        #shellcheck disable=SC1090 # Do not complain about not being able to follow
        . "$EC_CACHECONFFIL"
    else
        # Just consider cache disabled, don't log stuff every two minutes or so
        # date "+%H:%M:%S EC_CACHECONFFIL: ${EC_CACHECONFFIL} is not readable (cache upload disabled)"
        exit 0
    fi

    # Check cache config settings
    if [ -n "$CACHE_SERVER" ]; then
        if [ -z "$CACHE_SSH_KEY_FILE" ]; then
            date "+%H:%M:%S Cache server defined, but CACHE_SSH_KEY_FILE is undefined or empty (cache upload disabled)"
            unset CACHE_SERVER
        else
            if [ ! -r "$CACHE_SSH_KEY_FILE" ]; then
                date "+%H:%M:%S CACHE_SSH_KEY_FILE: ${CACHE_SSH_KEY_FILE} is unreadable (cache upload disabled)"
                unset CACHE_SERVER
            fi
        fi
    fi

    if [ -n "$CACHE_SERVER" ]; then
        CACHE_PORT=${CACHE_PORT-"22"}
        export NIX_SSHOPTS="-i${CACHE_SSH_KEY_FILE} -p${CACHE_PORT}"

        EC_THIS_SERVER="$(<"$EC_THISSRVFIL")"
        EC_SIGNATURE_RE="${EC_SIGNATURE_RE-"[a-z0-9]{32}-.*-${EC_THIS_SERVER}.signature"}"

        date "+%H:%M:%S Getting list of already copied images and build info files"

        # List all signature files for this server on cache
        # shellcheck disable=SC2086 # SSHOPTS must be unquoted here
        if ssh -n -oBatchMode=yes $NIX_SSHOPTS "$CACHE_SERVER" find /nix/store -regextype posix-extended -maxdepth 1 -regex "^/nix/store/$EC_SIGNATURE_RE\$" > "$EC_INCACHE"; then
            date "+%H:%M:%S Finding new files to copy"

            # List all signature files and remove copied ones to get list of new files
            if find /nix/store -regextype posix-extended -maxdepth 1 -regex "^/nix/store/$EC_SIGNATURE_RE\$" | grep -vxFf "$EC_INCACHE" > "$EC_NEWCACHE"; then
                date "+%H:%M:%S Nix copying stuff..."

                # Copy new files to cache
                xargs -a "$EC_NEWCACHE" -L 10 nix-copy-closure --to "$CACHE_SERVER"
            fi
        fi
        date "+Done at %d.%m.%4Y %H:%M:%S"
    fi
} >> "$EC_LOG" 2>&1

# Keep 20000 lines of log at maximum
Truncate_from_start "$EC_LOG" 20000
