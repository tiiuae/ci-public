#!/root/.nix-profile/bin/bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
#
# Copy image files to web server
#

SRVFIL="/home/hydra/webserver_ip.txt"
SFTPUSER="sftp_user"
TRIGUSER="script_trigger"
SFTPKEYFIL="/home/hydra/.ssh/websrv_sftp_key"
TRIGKEYFIL="/home/hydra/.ssh/websrv_trigger_key"

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
        echo "mkdir ${dir}"
        echo "cd ${dir}"
    done

    # To exit the sftp session
    echo "quit"
}

if [ ! -f "$SRVFIL" ] || [ ! -f "$SFTPKEYFIL" ] || [ ! -f "$TRIGKEYFIL" ] ; then
    exit 0
fi

SRV="$(cat "$SRVFIL")"
ORIGIN="$1"
shift

case "$ORIGIN" in
check-script)
    if shellcheck "${0}" && bashate -i E006 "${0}"; then
        echo Nothing to complain
    fi
    exit 1
;;
""|--help|-h)
    echo "Usage: ${0} ORIGIN [NIXSTOREPATH] ..." >&2
    echo "       ${0} check-script" >&2
    echo "" >&2
    echo "          ORIGIN = Origin of the file" >&2
    echo "    NIXSTOREPATH = Path to /nix/store" >&2
    echo "             ... = More paths to /nix/store" >&2
    echo "" >&2
    echo "    check-script = Run shellcheck and bashate on the script itself" >&2
    echo ""
    echo "Example: ${0} hydra /nix/store/sld9gfvca2l9y3zh5bnpw0j9axhyz7sa-generic-x86_64-debug-nixos.img" >&2
    echo "" >&2
    exit 1
;;
esac

while [ -n "$1" ]; do
    FULL="$1"
    # If path is a file and it looks like an nixos image file
    if [ -f "$FULL" ] && [[ $FULL =~ ^\/nix\/store\/[a-z0-9]{32}-.*-nixos\.img$ ]]; then
        # Remove prefix to get plain filename
        FILE="${FULL#/nix/store/}"
        # Remove hash and dash from filename
        TGT="${FILE:33}"
        # Also remove image postfix to get the target name
        TGT="${TGT%-nixos.img}"
        DIR="images/${ORIGIN}/${TGT}/"
        if wget -q --spider "https://${SRV}/files/${DIR}/${FILE}"; then
            echo "${FILE} already available on the web server" >&2
        else
            Sftp_mkdir_cmd "/upload/${DIR}" | sftp -i "$SFTPKEYFIL" "${SFTPUSER}@${SRV}" > /dev/null 2>&1
            if scp -s -i "$SFTPKEYFIL" "$1" "${SFTPUSER}@${SRV}:/upload/${DIR}"; then
                ssh -i "$TRIGKEYFIL" "${TRIGUSER}@${SRV}" -- "--sha256 ${DIR}${FILE}"
            fi
        fi
    fi
    shift
done
