#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2024 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Stop on error
set -e

# Required installed commands
PREREQUISITES=( "python3 --version" "wget -V" "tar --version" "xxd -v" "openssl version" "find --version" "mktemp --version" "realpath --version" "chmod --version" "grep --version" "mv --version" "rm --version" )

# URL prefix for the build reports
REPURL="https://vedenemo.dev/files/build_reports"

# URL for the sha256tree.py
SHA256URL="https://raw.githubusercontent.com/tiiuae/ci-public/main/sha256tree/sha256tree.py"

# URL for the server keys
KEYURL="https://vedenemo.dev/files/keys/"

# Default directory for server keys
KEYDIR="${CHECKSIG_KEYDIR:-$HOME/.ghafkeys}"

# Destination directory
DSTDIR="."

# Silenceable echo
function Echo {
    if [ -z "$QUIET" ]; then
        echo "$@"
    fi
}

# Calculate sha256 for a file or a directory
function Calc_sha256sum {
    python3 "${KEYDIR}/sha256tree.py" --plain -- "$1"
}

# Function to clear temp
function On_exit {
    if [ -n "$MYTEMP" ]; then
        cd /
        # Remove read-only attributes so files can be removed
        chmod -R u+w "$MYTEMP"
        rm -rf "$MYTEMP"
    fi
}

# Check given prerequisites (given commands can be executed)
function Check_prerequisites {
    local notfound=0
    local verbose

    if [ "$1" = "-v" ]; then
        verbose="1"
        shift
    fi

    while [ -n "$1" ]; do
        if ! $1 > /dev/null 2>&1; then
            echo "Error: Command \"${1% *}\" not found!" >&2
            notfound=1
        else
            if [ -n  "$verbose" ]; then
                echo "Command \"${1% *}\" found."
            fi
        fi
        shift
    done

    if [ $notfound -eq 1 ]; then
        exit 1
    fi
}

# Check signature, signature file name given as parameter
function Check_signature {
    local item hydra sig sign hash dgstbin sigfile
    sig="$1"

    # Remove .signature from end
    item="${sig::-10}"
    # Save to hydra
    hydra="$item"
    # Remove -<server name> from end
    item="${item%-*}"
    # Get only the -<server name> in hydra
    hydra="${hydra#"$item"}"
    # Remove dash
    hydra="${hydra:1}"
    # Remove nix-store hash from start to get the item name
    item="${item#[a-z0-9]*-}"

    if [ ! -e "$item" ]; then
        echo "${item} not found!" >&2
        exit 1
    fi

    if [ ! -r "${KEYDIR}/${hydra}.pub" ]; then
        Echo "Downloading key for ${hydra} server"
        wget -q "${KEYURL}/${hydra}.pub" -O "${KEYDIR}/${hydra}.pub"
    fi

    sign="$(<"$sig")"
    hash="$(Calc_sha256sum "$item")"

    # Remove carriage returns (just in case)
    hash="${hash//$'\r'/}"
    sign="${sign//$'\r'/}"

    # Remove new lines (just in case)
    hash="${hash//$'\n'/}"
    sign="${sign//$'\n'/}"

    # Check for valid input as xxd -r will silently ignore errors
    if [[ ! $hash =~ ^[0-9A-Fa-f]{64}$ ]]; then
        echo "${item}: Hash calculation failed" >&2
        exit 1
    fi

    dgstbin="$(mktemp -p "$MYTEMP")"
    sigfile="$(mktemp -p "$MYTEMP")"

    xxd -r -p <<< "$hash" > "$dgstbin"
    openssl enc -base64 -d -in - -out "$sigfile" <<< "$sign"

    if ! openssl dgst -sha256 -verify "${KEYDIR}/${hydra}.pub" -signature "$sigfile" "$dgstbin" > /dev/null 2>&1; then
        echo "${item}: Signature check failed" >&2
        exit 1
    fi
    echo "${item}: Signature check ok"

    # Remove item from unsigned list
    for I in "${!UNSIGNED[@]}"; do
        if [ "${UNSIGNED[I]}" = "$item" ]; then
            unset 'UNSIGNED[I]'
        fi
    done

    rm -rf "$dgstbin" "$sigfile"
}

# Show usage help
function Help {
    echo "Usage: $0 [options] SIGNEDITEM"
    echo ""
    echo "  SIGNEDITEM = Path or URL to item to check signature for"
    echo ""
    echo "Options:"
    echo "      --help, -h = Show this help"
    echo "     --quiet, -q = Show less status messages"
    echo "          -C DIR = Change directory before doing anything, create if not existing"
    echo " --keydir KEYDIR = Use alternate server key directory, create if not existing (default: ~/.ghafkeys)"
    echo "                   (You can also set CHECKSIG_KEYDIR environment variable instead)"
    echo "       --nocheck = Do not explicitly check for prerequisites"
    echo "        --prereq = Just check the prerequisites"
    echo "  --check-script = Run shellcheck and bashate on the script itself"
    echo "         --clear = Remove server key directory and exit"
    echo "    --sha256tree = Update sha256tree.py from repo even if it exists locally"
    echo "        --nosave = Do not save extracted package content"
    echo "              -- = Mark end of options (in case filename starts with a dash)"
    echo ""
    exit 0
}

# Run function on exit
trap On_exit EXIT

while [ -z "$1" ] || [[ $1 == -* ]]; do
    case "$1" in
    --help|-h|"")
        Help
    ;;
    --quiet|-q)
        QUIET=1
    ;;
    --nosave)
        NOSAVE=1
    ;;
    --nocheck)
        NOCHECK=1
    ;;
    --prereq)
        Check_prerequisites -v "${PREREQUISITES[@]}"
        exit 0
    ;;
    --check-script)
        if shellcheck --help > /dev/null 2>&1 && bashate --help > /dev/null 2>&1; then
            if shellcheck "$0" && bashate -i E006 "$0"; then
                echo "Nothing to complain"
            fi
        else
            echo "Please install shellcheck and bashate to use check-script functionality" >&2
        fi
        exit 0
    ;;
    --clear)
        chmod -R u+rw "$KEYDIR"
        rm -rf "$KEYDIR"
        exit 0
    ;;
    --sha256tree)
        GETSHA256=1
    ;;
    -C)
        shift
        if [ -n "$1" ]; then
            DSTDIR="$(realpath "$1")"
            mkdir -p "$DSTDIR"
            cd "$DSTDIR"
        else
            echo "Directory parameter missing" >&2
            exit 1
        fi
    ;;
    --keydir)
        shift
        if [ -n "$1" ]; then
            KEYDIR="$(realpath "$1")"
        else
            echo "Server key directory parameter missing" >&2
            exit 1
        fi
    ;;
    --)
        :
    ;;
    -*)
        echo "Invalid parameter: $1" >&2
        exit 1
    ;;
    esac

    shift
done

if [ -z "$NOCHECK" ]; then
    Check_prerequisites "${PREREQUISITES[@]}"
fi

# Make sure paths are absolute
KEYDIR="$(realpath "$KEYDIR")"
DSTDIR="$(realpath "$DSTDIR")"

if [ ! -d "$KEYDIR" ]; then
    # Create key dir
    mkdir -p "$KEYDIR"
    # Deny group and other access to files
    chmod 0700 "$KEYDIR"
fi

case "$1" in
https:*|http:*|ftp:*)
    # Get just the filename
    TARGET="$(realpath "./${1##*/}")"
    if [ -f "$TARGET" ]; then
        Echo "${TARGET} exists, skipping download"
    else
        Echo "Downloading $1"
        wget -q --show-progress "$1" -O "$TARGET"
    fi
;;
*)
    # Make sure given path is absolute
    TARGET="$(realpath "$1")"
;;
esac

# If sha256tree script is not in key dir, download it
if [ -n "$GETSHA256" ] || [ ! -f "${KEYDIR}/sha256tree.py" ]; then
    Echo "Downloading sha256tree.py"
    wget -q "$SHA256URL" -O "${KEYDIR}/sha256tree.py"
fi

# Check that target looks like an output package
if [[ $TARGET =~ ^.*-[a-z0-9_.]+-[0-9]+\.tar\.(xz|zstd?|gz|bz2)$ ]]; then
    MYTEMP=$(mktemp -d)
    mkdir -p "${MYTEMP}/package_contents"
    cd "${MYTEMP}/package_contents"

    Echo "Extracting ${TARGET} to temp dir"
    # extract, keep old (prevents overwriting ./ permissions), filename
    tar xkf "$TARGET"

    # Get list of all non-signature stuff in package
    mapfile -t UNSIGNED <<< "$(find . -mindepth 1 -maxdepth 1 -not -name "*.signature" -printf "%P\n")"

    for SIG in *.signature; do
        if [ "$SIG" = "*.signature" ]; then
            echo "${TARGET}: No signatures present" >&2
            exit 1
        else
            Check_signature "$SIG"
        fi
    done

    # If there are leftover entries in UNSIGNED array, there was something unsigned inside the package
    if [ "${#UNSIGNED[@]}" -ne "0" ]; then
        echo "Unsigned content in the package:" >&2
        for UNS in "${UNSIGNED[@]}"; do
            echo "  $UNS" >&2
        done
        exit 1
    fi

    if [ -z "$NOSAVE" ]; then
        # Make sure mv can remove files afterwards
        chmod -R u+w "${MYTEMP}/package_contents"
        Echo "Moving extracted files to ${DSTDIR}/package_contents"
        mv -f "${MYTEMP}/package_contents" "$DSTDIR"
    fi

else
    if [[ $TARGET =~ ^.*-[a-z0-9_.]+-[0-9]+-provenance\.json$ ]]; then
        MYTEMP=$(mktemp -d)

        # Remove -provenance.json from end
        BUILD="${TARGET::-16}"
        # Save to HYDRA
        HYDRA="$BUILD"
        # Remove everything before dash -> build number
        BUILD="${BUILD##*-}"
        # Remove dash and buildnumber from end
        HYDRA="${HYDRA%"-$BUILD"}"
        # Remove everything before and including last dash -> server name
        HYDRA="${HYDRA##*-}"
        FILNAM="${TARGET##*/}"
        for SIG in *-"${FILNAM}"-"${HYDRA}".signature; do
            if [ "${SIG:0:1}" = "*" ]; then
                Echo "No signature file found, checking build report"
                SIG="$(wget -q "${REPURL}/${HYDRA}/${BUILD}/" -O -)"
                SIG="$(grep ".*-${FILNAM}-${HYDRA}.signature" <<< "$SIG")"
                if [ -z "$SIG" ]; then
                    echo "Could not find provenance file signature on build report" >&2
                    exit 1
                fi
                SIG="${SIG#*\"}"
                SIG="${SIG%%\"*}"
                Echo "${SIG} found on build report, downloading"
                wget -q "${REPURL}/${HYDRA}/${BUILD}/${SIG}" -O "${SIG}"
            fi

            UNSIGNED=()
            Check_signature "$SIG"
        done
    else
        echo "${TARGET}: Does not look like a Ghaf package or provenance file" >&2
        exit 1
    fi
fi
