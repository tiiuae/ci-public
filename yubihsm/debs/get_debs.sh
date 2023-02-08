#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

TARBALL="yubihsm2-sdk-2023-01-ubuntu2204-amd64.tar.gz"

if [ ! -f "$TARBALL" ]; then
	wget "https://developers.yubico.com/YubiHSM2/Releases/$TARBALL"
fi

tar zxvf "$TARBALL" --strip-components 1 \
  yubihsm2-sdk/yubihsm-auth_2.4.0_amd64.deb \
  yubihsm2-sdk/libyubihsm-dev_2.4.0_amd64.deb \
  yubihsm2-sdk/libyubihsm1_2.4.0_amd64.deb \
  yubihsm2-sdk/yubihsm-setup_2.3.1-1_amd64.deb \
  yubihsm2-sdk/yubihsm-wrap_2.4.0_amd64.deb \
  yubihsm2-sdk/yubihsm-pkcs11_2.4.0_amd64.deb \
  yubihsm2-sdk/yubihsm-connector_3.0.4-1_amd64.deb \
  yubihsm2-sdk/yubihsm-shell_2.4.0_amd64.deb \
  yubihsm2-sdk/libyubihsm-usb1_2.4.0_amd64.deb \
  yubihsm2-sdk/libykhsmauth1_2.4.0_amd64.deb \
  yubihsm2-sdk/libyubihsm-http1_2.4.0_amd64.deb
