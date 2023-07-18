#!/root/.nix-profile/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

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
    trap "set +x; sleep 1.123h; set -x" DEBUG
fi

# Allow overriding any of the config variables
EC_WRITEDIR="${EC_WRITEDIR-"/home/hydra/extracopy"}"
EC_LOCK="${EC_LOCK-"/tmp/extracopy.lock"}"
EC_LOG="${EC_LOG-"${EC_WRITEDIR}/extracopy.log"}"
EC_INCACHE="${EC_INCACHE-"${EC_WRITEDIR}/extracopy.incache"}"
EC_ONWEBSRV="${EC_ONWEBSRV-"${EC_WRITEDIR}/extracopy.onweb"}"
EC_NEWCACHE="${EC_NEWCACHE-"${EC_WRITEDIR}/extracopy.newfiles.cache"}"
EC_NEWWEB="${EC_NEWWEB-"${EC_WRITEDIR}/extracopy.newfiles.web"}"
EC_RELATED="${EC_RELATED-"${EC_WRITEDIR}/extracopy.related"}"
EC_IMGPSTFX="${EC_IMGPSTFX-"-nixos.img"}"
EC_IMAGE_RE="${EC_IMAGE_RE-"[a-z0-9]{32}-.*-nixos\\.img"}"
EC_BINFO_RE="${EC_BINFO_RE-"[a-z0-9]{32}-.*-build-info\\.json"}"
EC_CACHESRVFIL="${EC_CACHESRVFIL-"/home/hydra/upload_ip.txt"}"
EC_CACHEPORTFIL="${EC_CACHEPORTFIL-"/home/hydra/upload_port.txt"}"
EC_CACHESSHKEY="${EC_CACHESSHKEY-"/home/hydra/.ssh/key"}"
EC_THISSRVFIL="${EC_THISSRVFIL-"/setup/postbuildsrv.txt"}"
EC_WEBSRVFIL="${EC_WEBSRVFIL-"/home/hydra/webserver_ip.txt"}"
EC_SFTPUSER="${EC_SFTPUSER-"sftp_user"}"
EC_TRIGUSER="${EC_TRIGUSER-"script_trigger"}"
EC_SFTPKEYFIL="${EC_SFTPKEYFIL-"/home/hydra/.ssh/websrv_sftp_key"}"
EC_TRIGKEYFIL="${EC_TRIGKEYFIL-"/home/hydra/.ssh/websrv_trigger_key"}"

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

# Gets outputs and derivations from list of build info files
# $1 = File containing list of files
# $2 = Output file (One line per path)
function Get_outputs_and_derivations {
    local path

    # Truncate/create empty output file
    truncate -s0 "$2"

    # Read file list one by one
    while IFS= read -r f; do
        # If it looks like a build info file and it exists
        if [[ $f =~ ^/nix/store/${EC_BINFO_RE}$ ]] && [ -f "$f" ]; then
            # Extract output path from json
            path="$(jq --raw-output '.outputs[0].path' "$f")"
            # If valid value was read then add it to output file
            if [[ $path != null ]]; then
                echo "$path" >> "$2"
            fi
            # Extract derivation path from json
            path="$(jq --raw-output .drvPath "$f")"
            # If valid value was read then add it to output file
            if [[ $path != null ]]; then
                echo "$path" >> "$2"
            fi
        fi
    done < "$1"
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


case "$1" in
"")
    : # Pass
;;
check-script)
    # This not intended to be used inside the hydra container
    # Just to check for errors on development environment that has shellcheck and bashate installed
    if shellcheck "${0}" && bashate -i E006 "${0}"; then
        echo Nothing to complain
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

# Create dir for logs
mkdir -p "$EC_WRITEDIR" || exit

# This is not meant to be thread safe locking, just enough to not start another copy process from cron
# if earlier one is still running

# If already running, just exit
if [ -f "$EC_LOCK" ]; then
    exit 0
fi

# Create lock file
touch "$EC_LOCK"

# Run On_exit function on exit
trap On_exit EXIT

# stdout and stderr are redirected to log file in following block
{
    date "+%d.%m.%4Y %H:%M:%S ------------------------------------"

    if [ -f "$EC_CACHESRVFIL" ] && [ -f "$EC_CACHESSHKEY" ]; then
        NIX_SSHOPTS="-i ${EC_CACHESSHKEY}"
        if [ -f "$EC_CACHEPORTFIL" ] ; then
            NIX_SSHOPTS+=" -p $(<"$EC_CACHEPORTFIL")"
        fi
        export NIX_SSHOPTS
        NIXCOPYTO="$(<"$EC_CACHESRVFIL")"

        date "+%H:%M:%S Getting list of already copied images and build info files"

        # List all images and build info files on cache
        # shellcheck disable=SC2086 # SSHOPTS must be unquoted here
        ssh -n $NIX_SSHOPTS "$NIXCOPYTO" find /nix/store -regextype posix-extended -maxdepth 1 \\\( -regex "^/nix/store/$EC_IMAGE_RE\$" -o -regex "^/nix/store/$EC_BINFO_RE\$" \\\) > "$EC_INCACHE"

        date "+%H:%M:%S Finding new files to copy"

        # List all images and build info files and remove copied ones to get list of new files
        find /nix/store -regextype posix-extended -maxdepth 1 \( -regex "^/nix/store/$EC_IMAGE_RE\$" -o -regex "^/nix/store/$EC_BINFO_RE\$" \) | grep -vxFf "$EC_INCACHE" > "$EC_NEWCACHE"

        date "+%H:%M:%S Nix copying stuff..."

        # Copy new files to cache
        xargs -a "$EC_NEWCACHE" -L 10 nix-copy-closure --to "$NIXCOPYTO"

        date "+%H:%M:%S Finding outputs and derivations"

        Get_outputs_and_derivations "$EC_NEWCACHE" "$EC_RELATED"

        date "+%H:%M:%S Copying outputs and derivations..."
        # Copy outputs and derivations to cache
        xargs -a "$EC_RELATED" -L 10 nix-copy-closure --to "$NIXCOPYTO"
    else
        date "+%H:%M:%S Cache uploading not configured"
    fi

    if [ -f "$EC_WEBSRVFIL" ] && [ -f "$EC_SFTPKEYFIL" ] && [ -f "$EC_TRIGKEYFIL" ] && [ -f "$EC_THISSRVFIL" ]; then
        WEBSRV="$(<"$EC_WEBSRVFIL")"
        THISSRV="$(<"$EC_THISSRVFIL")"

        date "+%H:%M:%S Getting list of dirs for this server on web server"
        # Get list of directories for this server
        WEBDIRS="$(wget -q -O - "https://${WEBSRV}/files/images/${THISSRV}" | grep -E "^<a href=\".*/\"" | cut -d\" -f2)"

        # Create or truncate list file
        truncate -s0 "$EC_ONWEBSRV"

        date "+%H:%M:%S Getting list of image files in the directories"
        # List image files in every directory for this server
        for DIR in $WEBDIRS; do
            wget -q -O - "https://${WEBSRV}/files/images/${THISSRV}/${DIR}" | grep -E "^<a href=\"$EC_IMAGE_RE\"" | cut -d\" -f2 | sed "s#^#/nix/store/#" >> "$EC_ONWEBSRV"
        done

        # Remove duplicates (There are a lot of symbolic links on web server for backwards compatibility at the moment, so this is actually useful)
        sort -u "$EC_ONWEBSRV" -o "$EC_ONWEBSRV"

        date "+%H:%M:%S Finding new image files in local store"
        # List images we have, and remove ones that are already on the web server
        find /nix/store -regextype posix-extended -maxdepth 1 -regex "^/nix/store/$EC_IMAGE_RE\$" | grep -vxFf "$EC_ONWEBSRV" > "$EC_NEWWEB"

        date "+%H:%M:%S Copying images to web server if any"
        while read -r FULL; do
            # If path is a file
            if [ -f "$FULL" ]; then
                # Remove prefix to get plain filename
                FILE="${FULL#/nix/store/}"
                # Look for matching signature file
                SIGNF="$(find /nix/store/*"-${FILE}-${EC_THISSRV}.signature" 2>/dev/null | head -n 1)"

                # If not signed yet, try to sign now.
                if [ -z "${SIGNF}" ] ; then
                    /home/hydra/scripts/sign.sh "${FULL}"
                    # TODO: Should sign.sh provide this information directly to us?
                    SIGNF="$(find /nix/store/*"-${FILE}-${EC_THISSRV}.signature" 2>/dev/null | head -n 1)"
		fi

                # Remove hash and dash from filename
                TGT="${FILE:33}"
                # Also remove image postfix to get the target name
                TGT="${TGT%"$EC_IMGPSTFX"}"
                DIR="images/${THISSRV}/${TGT}/"
                date "+%H:%M:%S Creating directory /upload/${DIR} (Remote mkdir failures are expected for existing directories)"
                Sftp_mkdir_cmd "/upload/${DIR}" | sftp -b - -i "$EC_SFTPKEYFIL" "${EC_SFTPUSER}@${WEBSRV}" > /dev/null
                if scp -B -s -i "$EC_SFTPKEYFIL" "$FULL" "${EC_SFTPUSER}@${WEBSRV}:/upload/${DIR}"; then
                    date "+%H:%M:%S Running trigger for ${FILE}"
                    ssh -n -i "$EC_TRIGKEYFIL" "${EC_TRIGUSER}@${WEBSRV}" -- "--sha256 ${DIR}${FILE}"
                    if [ -n "${SIGNF}" ] ; then
                        if scp -B -s -i "$EC_SFTPKEYFIL" "$SIGNF" "${EC_SFTPUSER}@${WEBSRV}:/upload/${DIR}"; then
                            date "+%H:%M:%S Running trigger for ${SIGNF}"
                            ssh -n -i "$EC_TRIGKEYFIL" "${EC_TRIGUSER}@${WEBSRV}" -- "${DIR}${SIGNF}"
                        else
                            date "+%H:%M:%S Copying ${SIGNF} failed"
                        fi
                    fi
                else
                    date "+%H:%M:%S Copying ${FULL} failed"
                fi
            fi
        done < "$EC_NEWWEB"
    else
        date "+%H:%M:%S Web copying not configured"
    fi

    date "+Done at %d.%m.%4Y %H:%M:%S"
} >> "$EC_LOG" 2>&1

# Keep 20000 lines of log at maximum
Truncate_from_start "$EC_LOG" 20000
