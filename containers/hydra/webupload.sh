#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# exit on error
set -e

# Remove lock file on exit
function On_exit {
    rm -f "$WU_LOCK"
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

# Sftp_mkdir_cmd function makes a command sequence for sftp that creates the
# given path on the server
# $1 = Path to create
function Sftp_mkdir_cmd {
    local patharr
    local str

    str="$1"

    # If path starts with slash, remove the leading slash
    if [[ $str == /* ]]; then
        str="${str:1}"
    fi

    # Split path to an array using slashes as separator
    IFS=/ read -r -a patharr <<< "$str"

    # Echo mkdir and cd for each directory
    for dir in "${patharr[@]}"; do
        # mkdir may fail if directory exists, thus dash prefix
        echo "-mkdir ${dir}"
        # chdir may not fail, thus no dash prefix
        echo "cd ${dir}"
    done

    # To exit the sftp session
    echo "quit"
}

# This is intended for debugging the script outside hydra container
# pkill is not available inside the hydra containter atm
if [ -n "$WU_DEBUG" ]; then
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
WU_WRITEDIR="${WU_WRITEDIR-"/home/hydra/webupload"}"
WU_LOCK="${WU_LOCK-"/tmp/webupload.lock"}"
WU_LOG="${WU_LOG-"${WU_WRITEDIR}/webupload.log"}"
WU_ONWEBSRV="${WU_ONWEBSRV-"${WU_WRITEDIR}/webupload.onweb"}"
WU_THISSRVFIL="${WU_THISSRVFIL-"/setup/postbuildsrv.txt"}"
WU_WEBCONFFIL="${WU_WEBCONFFIL-"/home/hydra/confs/webserver.conf"}"
WU_OUTPUT_RE="${WU_OUTPUT_RE-"[a-z0-9]{32}-.*\\.tar\\.xz"}"
WU_UPLOAD_DIR="${WU_UPLOAD_DIR-"/home/hydra/toupload"}"
WU_UPLOADED_DIR="${WU_UPLOADED_DIR:-"/home/hydra/uploaded"}"

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
    echo "Script for copying build outputs to web server"
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
if [ -f "$WU_LOCK" ]; then
    exit 0
fi

# Run On_exit function on exit
trap On_exit EXIT

# Create lock file
touch "$WU_LOCK"

mkdir -p "$WU_WRITEDIR"
mkdir -p "$WU_UPLOAD_DIR"
mkdir -p "$WU_UPLOADED_DIR"

# Garbage collect uploaded directory
# Uploaded files kept few days for debugging issues
find "$WU_UPLOADED_DIR" -type f -mtime +4 -delete
find "$WU_UPLOADED_DIR" -mindepth 1 -type d -empty -delete

# stdout and stderr are redirected to log file in following block
{
    if [ -r "$WU_WEBCONFFIL" ] ; then
        date "+%d.%m.%4Y %H:%M:%S ------------------------------------"
        # date "+%H:%M:%S Sourcing $WU_WEBCONFFIL"
        # shellcheck disable=SC1090 # Do not complain about not being able to follow
        . "$WU_WEBCONFFIL"
    else
        # Just consider webupload disabled, no need to flood log
        exit 0
    fi

    # Check web server config settings
    if [ -n "$WEB_SERVER" ] ; then
        CHECKLIST=("WEB_SFTP_KEY_FILE" "WEB_TRIG_KEY_FILE" "WEB_SFTP_USER" "WEB_TRIG_USER")

        for ITEM in "${CHECKLIST[@]}"; do
            if [ -z "${!ITEM}" ]; then
                date "+%H:%M:%S Web server defined, but ${ITEM} is undefined or empty (disabling web upload)"
                unset WEB_SERVER
            else
                if [[ $ITEM == *FILE ]] && [ ! -r "${!ITEM}" ]; then
                    date "+%H:%M:%S ${ITEM}: ${!ITEM} is unreadable (disabling web upload)"
                    unset WEB_SERVER
                fi
            fi
        done

        WEB_PROTO="${WEB_PROTO-"https"}"
        WEB_SSH_PORT="${WEB_SSH_PORT-"22"}"
        if [ -n "$WEB_PORT" ]; then
            WEB_PORT=":$WEB_PORT"
        fi

        if [ -r "$WU_THISSRVFIL" ]; then
            WU_THISSRV="$(<"$WU_THISSRVFIL")"
        else
            date "+%H:%M:%S WU_THISSRVFIL: ${WU_THISSRVFIL} is unreadable (disabling web upload)"
            unset WEB_SERVER
        fi
    fi

    if [ -n "$WEB_SERVER" ]; then
        # date "+%H:%M:%S Finding new output files in $WU_UPLOAD_DIR"
        # List output files we have
        WU_NEWWEB="$(find "$WU_UPLOAD_DIR" -regextype posix-extended -maxdepth 2 -regex "^.*/${WU_OUTPUT_RE}\$" -type f -printf '%P\n')"

        if [ -z "$WU_NEWWEB" ]; then
            date "+%H:%M:%S No new files to upload"
            exit 0
        fi

        date "+%H:%M:%S Getting list of dirs for this server on web server"
        # Get list of directories for this server
        WEBDIRS="$(wget -q -O - "${WEB_PROTO}://${WEB_SERVER}${WEB_PORT}/files/images/${WU_THISSRV}" | grep -E "^<a href=\".*/\"" | cut -d\" -f2)"

        # Create or truncate list file
        truncate -s0 "$WU_ONWEBSRV"

        date "+%H:%M:%S Getting list of output files in the directories"
        # List output files in every directory for this server
        for DIR in $WEBDIRS; do
            wget -q -O - "${WEB_PROTO}://${WEB_SERVER}${WEB_PORT}/files/images/${WU_THISSRV}/${DIR}" | grep -E "^<a href=\"$WU_OUTPUT_RE\"" | cut -d\" -f2  >> "$WU_ONWEBSRV"
        done

        # Remove duplicates
        sort -u "$WU_ONWEBSRV" -o "$WU_ONWEBSRV"

        pushd "$WU_UPLOAD_DIR" >/dev/null 2>&1
        date "+%H:%M:%S Copying files to web server if any"
        while read -r FN; do
            BN="$(basename "$FN")"
            if grep -q "^${BN}\$" "$WU_ONWEBSRV"; then
                # file is already on web server, move it to uploaded
                mkdir -p "${WU_UPLOADED_DIR}/${JOB}/"
                mv -f "$FN" "${WU_UPLOADED_DIR}/${JOB}/"
            else
                JOB="$(dirname "$FN")"
                DIR="images/${WU_THISSRV}/${JOB}/"
                date "+%H:%M:%S Creating directory /upload/${DIR} (Remote mkdir failures are expected for existing directories)"
                if Sftp_mkdir_cmd "/upload/${DIR}" | sftp -b - -i "$WEB_SFTP_KEY_FILE" -P "$WEB_SSH_PORT" "${WEB_SFTP_USER}@${WEB_SERVER}" > /dev/null; then
                    date "+%H:%M:%S Uploading $FN"
                    if scp -B -s -i "$WEB_SFTP_KEY_FILE" -P "$WEB_SSH_PORT" "$FN" "${WEB_SFTP_USER}@${WEB_SERVER}:/upload/${DIR}"; then
                        date "+%H:%M:%S Running trigger for $BN"
                        if ssh -n -o BatchMode=yes -i "$WEB_TRIG_KEY_FILE" "${WEB_TRIG_USER}@${WEB_SERVER}" -- "${DIR}${BN}"; then
                            # Move to uploaded
                            mkdir -p "${WU_UPLOADED_DIR}/${JOB}"
                            mv -f "$FN" "${WU_UPLOADED_DIR}/${JOB}"
                        else
                            date "+%H:%M:%S Trigger for ${FN} failed"
                        fi
                    else
                        date "+%H:%M:%S Copying ${FN} failed"
                    fi
                else
                    date "+%H:%M:%S Creating /upload/${DIR} failed"
                fi
            fi
        done <<< "$WU_NEWWEB"
        popd >/dev/null 2>&1
        date "+Done at %d.%m.%4Y %H:%M:%S"
    fi

} >> "$WU_LOG" 2>&1

# Keep 20000 lines of log at maximum
Truncate_from_start "$WU_LOG" 20000
