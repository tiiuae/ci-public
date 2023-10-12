#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Run the hydra docker container

# bash needed for '-s' and 'n' parameters for 'read'

# exit on error
set -e

# shellcheck disable=SC1091 # Don't complain about not following
. "confs/hydra.default"

# See README.hydra about the version
HYDRA_STORE_VERSION="3"

EXTRA_FLAGS="--privileged"

case "$1" in
check-script)
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
-h|--help)
    echo "Usage: $0 [store root=${HC_STORE_PATH} (from config)] [/srv mount=not in use] [debug mode=false]"
    exit
;;
"")
    if [ -z "$HC_STORE_PATH" ]; then
        echo "No store path set!" >&2
        exit 1
    fi
    STORE="$HC_STORE_PATH"
;;
*)
    STORE="$1"
;;
esac

case "$2" in
"")
    SRV="${HC_SRV_MOUNT}"
;;
"off")
    SRV=""
;;
*)
    SRV="$2"
;;
esac

case "${3,,}" in
true)
    CONTAINER_DEBUG="true"
;;
""|false)
    CONTAINER_DEBUG="false"
;;
*)
    echo "Unknown debug value \"$3\"!" >&2
    exit 1
;;
esac

if [ ! -d "$STORE" ] && [ "$HC_NONINTERACTIVE" != "on" ]; then
    echo "\"$STORE\" does not exist. Do you want it created now? (y/n)"
    echo -n "> "
    read -r -n 1 ANSWER
    echo
    if [ "${ANSWER,,}" != "y" ]; then
        echo "Aborted!" >&2
        exit 1
    fi
fi

if [ ! -f "${STORE}/format" ]; then
    if [ -f "${STORE}/initializing" ]; then
        echo "\"${STORE}\" has been (only) partially populated by earlier run." >&2
        echo "Don't know how to fix." >&2
        exit 1
    fi
    # First run.
    echo "First run - setting things up"
    echo

    if [ -z "$PW_ADMIN" ]; then
        while true; do
            echo "Give hydra admin password"
            echo -n "> "
            read -r -s PW_ADMIN
            echo ""
            echo "Confirm hydra admin password"
            echo -n "> "
            read -r -s PW_CONFIRM
            echo ""
            if [ "$PW_ADMIN" = "$PW_CONFIRM" ]; then
                break
            else
                echo "Passwords did not match." >&2
            fi
        done
    fi

    if [ -z "$PW_AUTO" ] ; then
        while true; do
            echo "Give hydra automation password"
            echo -n "> "
            read -r -s PW_AUTO
            echo
            echo "Confirm hydra automation password"
            echo -n "> "
            read -r -s PW_CONFIRM
            echo
            if [ "$PW_AUTO" = "$PW_CONFIRM" ] ; then
                break
            else
                echo "Passwords did not match." >&2
            fi
        done
    fi

    # Extra error handling removed, exit on error flag will do nicely here
    mkdir -p "${STORE}/nix" "${STORE}/home"

    touch "${STORE}/initializing"
    # Make sure we have absolute path
    STORE="$(realpath "$STORE")"

    echo "Copying store"
    # Mount store as /nix/outside, so the container can copy files between internal store and outside store
    # shellcheck disable=SC2086 # CONTAINER_DEBUG_ARG may contain space separated options for docker -> unquoted
    docker run \
        $EXTRA_FLAGS \
        --mount type=bind,source="${STORE}/nix",target=/nix/outside \
        --mount type=bind,source="${STORE}/home",target=/nix/outside_home \
        -e SETUP_RUN=1 $CONTAINER_DEBUG_ARG -t "${HC_BASE_LABEL}"

    # Mount store over the nix store, run rest of the setup
    mkdir -p "${STORE}/home"
    echo "Restarting container, running setup"
    # shellcheck disable=SC2086 # EXTRA_FLAGS purposefully unquoted
    docker run \
        $EXTRA_FLAGS \
        --mount type=bind,source="${STORE}/nix",target=/nix \
        --mount type=bind,source="${STORE}/home",target=/home/hydra \
        -e SETUP_RUN=2 -e PW_ADMIN="$PW_ADMIN" -e PW_AUTO="$PW_AUTO" \
        -t "${HC_BASE_LABEL}"
    echo "Restarting container, configuring hydra projects and jobsets"
    # shellcheck disable=SC2086 # EXTRA_FLAGS purposefully unquoted
    docker run --name "${HC_BASE_LABEL}-configure" -p "${HC_PORT}:3000" \
        $EXTRA_FLAGS \
        --mount type=bind,source="${STORE}/nix",target=/nix \
        --mount type=bind,source="${STORE}/home",target=/home/hydra \
        -t "${HC_BASE_LABEL}" &
    sleep 15
    if ! HYDRACTL_PASSWORD="$PW_AUTO" ./hydra/hydra-configure.sh "${HC_PORT}" ; then
        docker stop "${HC_BASE_LABEL}-configure"
        docker container rm "${HC_BASE_LABEL}-configure"
        echo "Hydra project setup failed" >&2
        exit 1
    fi
    docker stop "${HC_BASE_LABEL}-configure"
    docker container rm "${HC_BASE_LABEL}-configure"

    # First line is the version, we could add more information to later lines
    echo "${HYDRA_STORE_VERSION}" > "${STORE}/format"
    rm "${STORE}/initializing"
    echo
    echo "Setup ready. Use ./run_hydra again for regular run."
    exit
else
    # Make sure we have absolute path
    STORE="$(realpath "$STORE")"

    OLD_STORE_VERSION=$(head -n 1 "${STORE}/format")

    # Add conversions from old versions to current one here, once there's a new version
    if [ "${OLD_STORE_VERSION}" != "${HYDRA_STORE_VERSION}" ] ; then
        echo "Format of the existing store (version: ${OLD_STORE_VERSION}) not supported." >&2
        exit 1
    fi
fi

MOUNTS=" \
    --mount type=bind,source=${STORE}/nix,target=/nix \
    --mount type=bind,source=${STORE}/home,target=/home/hydra \
    "

if [ "$SRV" != "" ] ; then
    MOUNTS="$MOUNTS --mount type=bind,source=${SRV},target=/srv"
fi

KNOWN_HOSTS="${STORE}/home/.ssh/known_hosts"
if [ ${#HC_KNOWN_HOSTS[@]} -ne 0 ] && [ ! -f "$KNOWN_HOSTS" ]; then
    echo "Creating known_hosts"
    mkdir -p "$(dirname "$KNOWN_HOSTS")"
    touch "$KNOWN_HOSTS"
    chmod og-rwx "$(dirname "$KNOWN_HOSTS")" "$KNOWN_HOSTS"
    for host in "${HC_KNOWN_HOSTS[@]}"; do
        h_name="${host%%:*}"
        h_port="${host##*:}"
        echo "Scanning host key for ${h_name}:${h_port}"
        ssh-keyscan -H -p "$h_port" "$h_name" >> "$KNOWN_HOSTS" 2>/dev/null
    done
fi

HOSTS=""
for host in "${HC_CUSTOM_HOSTS[@]}"; do
    HOSTS+="--add-host=$host "
done

SETUPCONFIG="${STORE}/home/setup_config"
echo "# this is autogenerated from run_hydra.sh" > "$SETUPCONFIG"
echo "export HYDRA_URL=\"$HYDRA_URL\"" >> "$SETUPCONFIG"
echo "export HYDRA_NAME=\"$HC_PB_SRV\"" >> "$SETUPCONFIG"

# If both stdin and stdout are to/from tty, set interactive flag for docker run
# Allows exiting with ctrl-c
if [ -t 0 ] && [ -t 1 ]; then
    EXTRA_FLAGS+=" -i"
fi

if [ "$CONTAINER_DEBUG" = "true" ]; then
    # Debug run
    # shellcheck disable=SC2086 # EXTRA_FLAGS, MOUNTS and HOSTS purposefully unquoted
    docker run \
        --name "${HC_BASE_LABEL}-cnt" \
        -p "${HC_PORT}:3000" \
        $EXTRA_FLAGS \
        $MOUNTS \
        $HOSTS \
        -e SETUP_RUN="ext" \
        -t "${HC_BASE_LABEL}"
else
    # Regular run
    # shellcheck disable=SC2086 # EXTRA_FLAGS, MOUNTS and HOSTS purposefully unquoted
    docker run \
        --name "${HC_BASE_LABEL}-cnt" \
        -p "${HC_PORT}:3000" \
        $EXTRA_FLAGS \
        $MOUNTS \
        $HOSTS \
        -t "${HC_BASE_LABEL}"
fi
