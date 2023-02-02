#!/bin/sh

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie

# Create hydra user

HYDRA_UID="$1"
HYDRA_GID="$2"

cd /setup/

cp /etc/passwd passwd
echo "hydra:x:${HYDRA_UID}:${HYDRA_GID}:Hydra:/home/hydra:/bin/false" >> passwd
cp /etc/group group.tmp
echo "hydra:x:${HYDRA_GID}" >> group.tmp
NIXBLD_OLD="$(grep "^nixbld:" group.tmp)"
grep -v "${NIXBLD_OLD}" group.tmp > group
echo "${NIXBLD_OLD},hydra" >> group
rm group.tmp

mkdir -p /home/hydra/db

PWFILE=$(nix-store --add passwd)
GRFILE=$(nix-store --add group)

rm /etc/passwd
ln -s $PWFILE /etc/passwd

rm /etc/group
ln -s $GRFILE /etc/group

chown -R hydra:hydra /home/hydra

mkdir -p /var/lib/hydra
chown hydra:hydra /var/lib/hydra
