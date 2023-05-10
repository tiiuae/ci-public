# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container for the jenkins agent

FROM nixos/nix

RUN mkdir -p /setup/ /launch/
COPY channel.sh user.sh /setup/
COPY launch.sh run.sh /launch/
RUN chmod +x /launch/*.sh /setup/*.sh

ARG CHANNEL
RUN /setup/channel.sh "$CHANNEL"

ARG JAGENT_UID
ARG JAGENT_GID

RUN nix-env -i openjdk-headless -i openssh

RUN mkdir -p /nix/etc/ssh
COPY sshd_config /nix/etc/ssh/
RUN ln -s /nix/etc/ssh /etc/ssh
RUN mkdir -p /var/empty

RUN /setup/user.sh "$JAGENT_UID" "$JAGENT_GID"

RUN chown -R jenkins:jenkins /nix/var/nix

WORKDIR /launch
ENTRYPOINT /launch/launch.sh
