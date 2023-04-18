#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Create jenkins user

JCONTROL_UID="$1"
JCONTROL_GID="$2"

echo "jenkins:x:${JCONTROL_UID}:${JCONTROL_GID}:Jenkins:/jenkins:/bin/false" >> /etc/passwd
echo "jenkins:x:${JCONTROL_GID}" >> /etc/group
