# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)

FROM ubuntu:latest

COPY ./debs /debs

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y libpcsclite1 libcurl4 libusb-1.0-0 libedit2 
RUN dpkg -i /debs/*.deb
RUN mkdir /data

WORKDIR /data
