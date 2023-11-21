#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

############################################################################################################################

# Script for uploading results to web server and create target Hydra server directory if one not exist.
# Needed arguments
# $1: directory name (hydra instance name)
# $2: sftp key file
# $3: ssh port
# $4: sftp user
# $5: web server
# $6: build ID
# $7: trigger user
# $8: trigger key file

############################################################################################################################

##### Functions

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

#############
# Main
#############

if Sftp_mkdir_cmd /upload/build_reports/"$1" | sftp -b - -i "$2" -P "$3" "$4"@"$5" > /dev/null; then
    scp -s -i "$2" -r "$6" "$4"@"$5":/upload/build_reports/"$1"/"$6"
    ssh -i "$8" "$7"@"$5" -- --index build_reports/"$1"/"$6"
fi
