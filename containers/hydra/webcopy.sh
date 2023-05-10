#!/root/.nix-profile/bin/bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
#
# Copy image files to web server
#

if ! [ -f /home/hydra/webserver_ip.txt ] ||
   ! [ -f /home/hydra/.ssh/websrv_sftp_key ] ||
   ! [ -f /home/hydra/.ssh/websrv_trigger_key ] ; then
  exit 0
fi

SRV="$(cat /home/hydra/webserver_ip.txt)"
ORIGIN="$1"
shift

# All known platforms images may be handled for
PLATFORMS="orin nuc"

# Image names are just placeholders atm. TBD
declare -A IMAGES=(
    ["orin"]="-nvidia-jetson-orin-nixos.img -nvidia-jetson-orin-debug-nixos.img -nvidia-jetson-orin-release-nixos.img"
    ["nuc"]="-intel-nuc-nixos.img -intel-nuc-debug-nixos.img -intel-nuc-release-nixos.img"
)

while [ -n "$1" ]; do
    FULL="$1"
    if [[ "$FULL" == /nix/store/* ]]; then
        FILE="${FULL#/nix/store/}"
        for PFM in $PLATFORMS; do
            IMGS="${IMAGES["$PFM"]}"
            DIR="images/${ORIGIN}/${PFM}/"
            for I in $IMGS; do
	        if [[ "$FILE" == *${I} ]] && [ -f "$FULL" ]; then
                    if wget --spider "https://${SRV}/files/${DIR}/${FILE}" ; then
                        echo "${FILE} already available on web server" >&2
                    else
                        if scp -s -i /home/hydra/.ssh/websrv_sftp_key "$1" "sftp_user@${SRV}:/upload/${DIR}"; then
                            ssh -i /home/hydra/.ssh/websrv_trigger_key "script_trigger@${SRV}" -- "--sha256 ${DIR}${FILE}"
                        fi
                    fi
                fi
            done
        done
    else
        printf "Path outside /nix/store: %s\n" "$FULL" >&2
    fi
    shift
done
