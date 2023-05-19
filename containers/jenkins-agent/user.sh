#!/bin/sh

# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Create jenkins user

JENKINS_UID="$1"
JENKINS_GID="$2"

cd /setup/ || exit 1

cp /etc/passwd passwd
echo "sshd:x:150:65534::/run/sshd:/bin/false" >> passwd
echo "jenkins:x:${JENKINS_UID}:${JENKINS_GID}:Jenkins:/jenkins:/bin/sh" >> passwd
cp /etc/group group
echo "jenkins:x:${JENKINS_GID}:" >> group

PWFILE="$(nix-store --add passwd)"
GRFILE="$(nix-store --add group)"

rm /etc/passwd
ln -s "$PWFILE" /etc/passwd

rm /etc/group
ln -s "$GRFILE" /etc/group

mkdir -p /jenkins/.ssh
chmod go-rwx /jenkins/.ssh
echo "PATH=/root/.nix-profile/bin" > /jenkins/.ssh/environment

chown -R jenkins:jenkins /jenkins
