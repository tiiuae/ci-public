#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Sign a file or a directory


# Script setup parameters
SIGN_CONF="/home/hydra/confs/signing.conf"
SIGNTMPDIR="/home/hydra/signatures"
INSTANCE_FILE="/setup/postbuildsrv.txt"
PREREQUISITES=("cut --help" "python3 --version" "basename --help" "tail --help" "sort --help" "ssh -V" "nix-store --help")


# Check given prerequisites (given commands can be executed)
function Check_prerequisites {
    local notfound=0

    while [ -n "$1" ]; do
        if ! $1 > /dev/null 2>&1; then
            echo "Error: ${1% *} not found in path!" >&2
            notfound=1
        fi
        shift
    done

    if [ $notfound -eq 1 ]; then
        exit 1
    fi
}

# Calculate sha256 for a file or a directory
function Calc_sha256sum {
    python3 sha256tree.py --plain -- "$1"
}

case "$1" in
""|--help)
    echo "Usage: $0 [--|--sha256] PATH1 [PATH2] [...]"
    echo "       $0 [--help|--check-script|--prerequisites]"
    echo ""
    echo "           PATHn = PATH to a file or directory to be signed"
    echo "              -- = Use this in case you have paths starting with two dashes"
    echo "        --sha256 = Just calculate checksum for given paths"
    echo "          --help = Show this help message"
    echo "  --check-script = Run shellcheck and bashate on the script itself"
    echo " --prerequisites = Check for commands required to run the script"
    echo ""
    exit 0
;;
--check-script)
    # This not intended to be used inside the container
    # Just to check for errors on development environment that has shellcheck and bashate installed
    if shellcheck --help > /dev/null 2>&1 && bashate --help > /dev/null 2>&1; then
        if shellcheck "$0" && bashate -i E006 "$0"; then
            echo "Nothing to complain"
        fi
    else
        echo "Please install shellcheck and bashate to use check-script functionality"
    fi
    exit 0
;;
--prerequisites)
    # Check that commands are available
    Check_prerequisites "${PREREQUISITES[@]}"
    echo "All commands seem to work" >&2
    exit 0
;;
--sha256)
    shift
    while [ -n "$1" ]; do
        Calc_sha256sum "$1"
        shift
    done
    exit 0
;;
--)
    shift
;;
--*)
    echo "Invalid parameter: $1" >&2
    exit 1
;;
esac

if [ -f "$SIGN_CONF" ]; then
    # shellcheck disable=SC1090 # Shut up about not being able to follow non-constant source
    . "$SIGN_CONF"

    if [ -n "$SIGNING_SRV" ] && [ -n "$SIGNING_SRV_KEY_FILE" ] && [ -n "$SIGNING_SRV_PATH" ] && [ -n "$SIGNING_SRV_USER" ]; then
        SIGN_SSHOPTS="-i $SIGNING_SRV_KEY_FILE -l $SIGNING_SRV_USER"
        if [ -n "$SIGNING_PORT" ]; then
            SIGN_SSHOPTS+=" -p $SIGNING_PORT"
        fi

        # Check that commands are available
        Check_prerequisites "${PREREQUISITES[@]}"

        HYDRA_INSTANCE="$(< $INSTANCE_FILE)"
        mkdir -p "$SIGNTMPDIR" || { echo "Could not create $SIGNTMPDIR" >&2; exit 1; }

        while [ -n "$1" ]; do
            SHA256SUM="$(Calc_sha256sum "$1")"
            SIGNATURE_FILE="${SIGNTMPDIR}/$(basename "$1")-${HYDRA_INSTANCE}.signature"

            # shellcheck disable=SC2086 # $SIGN_SSHOPTS is purposefully unquoted here
            if ssh -n -o BatchMode=yes $SIGN_SSHOPTS "$SIGNING_SRV" "${SIGNING_SRV_PATH}/start.sh" sign "-h=$SHA256SUM" > "$SIGNATURE_FILE"; then
                # Remove carriage returns if any
                if sed -i "s/\r//g" "$SIGNATURE_FILE"; then
                    if STORE_SIGN_FILE="$(nix-store --add "$SIGNATURE_FILE")"; then
                        echo "$STORE_SIGN_FILE"
                    else
                        echo "Adding signature file to nix store failed" >&2
                    fi
                else
                    echo "Something went wrong when removing carriage returns form signature file" >&2
                fi
            else
                echo "Failed to sign $1" >&2
            fi
            # Remove temporary
            rm -f "$SIGNATURE_FILE"

            shift
        done
    else
        echo "${SIGN_CONF}: Invalid config" >&2
        exit 1
    fi
fi
