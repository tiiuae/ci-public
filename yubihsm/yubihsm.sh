#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

set -e

# Get actual directory of this bash script
SDIR="$(dirname "${BASH_SOURCE[0]}")"
SDIR="$(realpath "$SDIR")"

CONTAINER=yubihsm
RULEFILE=/etc/udev/rules.d/90-yubihsm2.rules
YUBIUID="$(id -u)"
YUBIGID="$(id -g)"
YUBIUSER="$(id -un "$YUBIUID")"

if [ -z "$1" ]; then
    echo "Usage: $0 [OPT...] CMD"
    echo ""
    echo "  OPT = Option"
    echo "  CMD = Command"
    echo ""
    echo "  Options:"
    echo "    --uid=UID   = Set container user id (default current user)"
    echo "    --gid=GID   = Set container group id (default current user group)"
    echo "    --user=USER = Set container user by name (default current username)"
    echo "    --force     = Set force flag for udev command"
    echo ""
    echo "    Setting just uid or username will set also gid to that user's group and"
    echo "    aĺso set uid or username whichever was not given."
    echo "    e.g. setting '--user=root' will imply '--uid=0' and '--gid=0'"
    echo ""
    echo "  Commands:"
    echo "    udev   = Install the udev rule for yubihsm2 device"
    echo "    build  = Build the yubishm container"
    echo "    start  = Start yubihsm container with yubihsm-connector"
    echo "    stop   = Stop yubihsm container"
    echo "    shell  = Open yubihsm shell"
    echo "    logs   = Show yubuhsm container log"
    echo "    remove = Remove container image"
    echo "    bash   = Open bash shell in container (use --uid=0 option to get a root shell)"
    exit 1
fi

while [[ $1 == --* ]]; do
    case "$1" in
    --uid=*)
        YUBIUID="${1##--uid=}"
        UIDGIVEN=1
        if [ -z "$GIDGIVEN" ]; then
            YUBIGID="$(id -g "$YUBIUID")"
        fi
        if [ -z "$USERGIVEN" ]; then
            YUBIUSER="$(id -un "$YUBIUID")"
        fi
    ;;
    --gid=*)
        YUBIGID="${1##--gid=}"
        GIDGIVEN=1
    ;;
    --user=*)
        YUBIUSER="${1##--user=}"
        USERGIVEN=1
        if [ -z "$UIDGIVEN" ]; then
            YUBIUID="$(id -u "$YUBIUSER")"
        fi
        if [ -z "$GIDGIVEN" ]; then
            YUBIGID="$(id -g "$YUBIUSER")"
        fi
    ;;
    --force)
        FORCE=1
    ;;
    --*)
        echo "Unknown option: $1"
        exit 1
    esac
    shift
done

if [ -z "$1" ]; then
    echo "Missing command"
    exit 1
fi

case "$1" in
udev)
    if [ -e "$RULEFILE" ]; then
        if [ -z "$FORCE" ]; then
            echo "$RULEFILE exists already"
            echo ""
            echo "if you are sure you know what you're doing,"
            echo "run this command with '--force' option to remove old udev rule first"
            exit 1
        else
            sudo rm -f "$RULEFILE"
        fi
    fi
    # Please note that actual tabs in the here-document are very much intentional, it is the only way
    # to get some indentation in the here-document.
    cat <<- EOF | sudo tee "$RULEFILE" > /dev/null
	# This udev rule base is from https://developers.yubico.com/YubiHSM2/Component_Reference/yubihsm-connector/
	# This udev file should be used with udev 188 and newer
	ACTION!="add|change", GOTO="yubihsm2_connector_end"
	
	# Yubico YubiHSM 2
	# The OWNER attribute here has to match the uid of the process running the Connector
	SUBSYSTEM=="usb", ATTRS{idVendor}=="1050", ATTRS{idProduct}=="0030", OWNER="$YUBIUSER"
	
	LABEL="yubihsm2_connector_end"
	EOF

    sudo udevadm control --reload-rules
    sudo udevadm trigger
;;
build)
    pushd "$SDIR" > /dev/null
    pushd ./debs > /dev/null
    . get_debs.sh
    popd > /dev/null

    sudo chgrp -R "$YUBIGID" ./data
    sudo chmod g+srwx ./data
    sudo chmod -R g+rw ./data
    docker build --build-arg YUBIHSM_UID="$YUBIUID" --build-arg YUBIHSM_GID="$YUBIGID" --tag "$CONTAINER" .
    popd > /dev/null
;;
start)
    pushd "$SDIR" > /dev/null
    docker run --name "$CONTAINER" --rm -itd --device=/dev/bus -v "$(pwd)"/data:/data "$CONTAINER" yubihsm-connector -d
    popd > /dev/null
;;
stop)
    docker stop "$CONTAINER"
;;
shell)
    docker exec -it "$CONTAINER" yubihsm-shell
;;
logs)
    docker logs "$CONTAINER"
;;
remove)
    docker rmi "$CONTAINER"
;;
bash)
    docker exec -it -u "$YUBIUID" "$CONTAINER" /bin/bash
;;
*)
    echo "Unknown command: $1"
    exit 1
;;
esac
