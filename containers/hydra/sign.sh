#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0


# Callback script called after a package has been built

if [ -f /home/hydra/confs/signing.conf ] ; then
  . /home/hydra/confs/signing.conf
  if [ -n "$SIGNING_SRV" ] && [ -n "$SIGNING_SRV_KEY_FILE" ] &&
     [ -n "$SIGNING_SRV_PATH" ] && [ -n "$SIGNING_SRV_USER" ] ; then
    if [ -n "$SIGNING_PORT" ] ; then
      export SIGN_SSHOPTS="-i $SIGNING_SRV_KEY_FILE -l $SIGNING_SRV_USER -p $SIGNING_PORT"
    else
      export SIGN_SSHOPTS="-i $SIGNING_SRV_KEY_FILE -l $SIGNING_SRV_USER"
    fi

    SIGNTMPDIR="/home/hydra/signatures"
    HYDRA_INSTANCE="$(cat /setup/postbuildsrv.txt)"
    mkdir -p "${SIGNTMPDIR}"

    for PTH in $@
    do
      SHA256SUM="$(sha256sum $PTH)"
      SIGNATURE_FILE="${SIGNTMPDIR}/$(basename "${PTH}")-${HYDRA_INSTANCE}.signature"

      ssh $SIGN_SSHOPTS "$SIGNING_SRV" "${SIGNING_SRV_PATH}/start.sh" \
	  --sign "--h=${SHA256SUM}" | tail -n 1 > "${SIGNATURE_FILE}"
      STORE_SIGN_FILE="$(nix-store --add "${SIGNATURE_FILE}")"

      echo "${STORE_SIGN_FILE}"

      # Remove temporary
      rm -f "${SIGNATURE_FILE}"
    done
  fi
fi
