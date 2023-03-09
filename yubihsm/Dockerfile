# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

FROM ubuntu:latest

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y libpcsclite1 libcurl4 libusb-1.0-0 libedit2

COPY ./debs /debs

RUN dpkg -i /debs/*.deb

ARG YUBIHSM_UID
ARG YUBIHSM_GID
RUN groupmod -g $YUBIHSM_GID yubihsm-connector
RUN usermod -u $YUBIHSM_UID -g $YUBIHSM_GID yubihsm-connector

USER yubihsm-connector
WORKDIR /data
