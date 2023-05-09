#!/root/.nix-profile/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Get actual directory of this bash script
SDIR="$(dirname "${0}")"
SDIR="$(realpath "$SDIR")"
WRITEDIR="/home/hydra/extracopy"

LOCK="/tmp/extracopy.lock"
LOG="${WRITEDIR}/extracopy.log"
COPIED="${WRITEDIR}/extracopy.copied"
NEWFILES="${WRITEDIR}/extracopy.newfiles"
RELATED="${WRITEDIR}/extracopy.related"
IMAGES="-nixos.img"
BINFOS="-build-info.json"

# Remove lock file on exit
function On_exit {
    rm -f "$LOCK"
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
        if [[ $f == *$BINFOS ]] && [ -f "$f" ]; then
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

# This is not meant to be thread safe locking, just enough to not start another copy process from cron
# if earlier one is still running

# If already running, just exit
if [ -f "$LOCK" ]; then
    exit 0
else
    # Create lock file
    touch "$LOCK"
fi

# Run On_exit function on exit
trap On_exit EXIT

# stdout and stderr are redirected to log file in following block
if [ -f /home/hydra/upload_ip.txt ] && [ -f /home/hydra/.ssh/key ] &&
   mkdir -p "${WRITEDIR}" ; then
{
    if [ -f /home/hydra/upload_port.txt ] ; then
      NIX_SSHOPTS="-i /home/hydra/.ssh/key -p $(cat /home/hydra/upload_port.txt)"
    else
      NIX_SSHOPTS="-i /home/hydra/.ssh/key"
    fi
    export NIX_SSHOPTS
    NIXCOPYTO="$(cat /home/hydra/upload_ip.txt)"

    cd "${SDIR}" || return

    echo "$(date) ------------------------------------"

    # Create empty copied file if not existing
    if [ ! -f "$COPIED" ]; then
        touch "$COPIED"
    fi

    # List all images and build info files and remove copied ones to get list of new files
    find /nix/store -maxdepth 1 \( -name "*${IMAGES}" -o -name "*${BINFOS}" \) | grep -vxFf "$COPIED" > "$NEWFILES"

    echo "Nix copying stuff..."

    # Copy new files to cache
    xargs -a "$NEWFILES" -L 10 nix-copy-closure --to "$NIXCOPYTO"

    Get_outputs_and_derivations "$NEWFILES" "$RELATED"

    echo "Copying outputs and derivations..."
    # Copy outputs and derivations to cache
    xargs -a "$RELATED" -L 10 nix-copy-closure --to "$NIXCOPYTO"

    if [ -f /home/hydra/webserver_ip.txt ] && [ -f /setup/postbuildsrv.txt ] ; then
      echo "Copying images to web server if any"
      THISSRV="$(cat /etc/postbuildsrv.txt)"
      # Copy images to webserver (webcopy.sh only acts on defined images)
      while IFS= read -r f; do
        if [ -f "$f" ]; then
          "${SDIR}/webcopy.sh" "$THISSRV" "$f"
        fi
      done < "$NEWFILES"
    fi

    # Add new ones to copied
    cat "$NEWFILES" >> "$COPIED"

    echo "Done at $(date)"

} >> $LOG 2>&1

  # Keep 20000 lines of log at maximum
  Truncate_from_start "$LOG" 20000

fi
