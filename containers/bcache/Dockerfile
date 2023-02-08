# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Marko Lindqvist <marko.lindqvist@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)

# Container for the hydra

FROM nixos/nix

RUN nix-env -i openssh -i nix-serve

RUN mkdir -p /nix/etc/ssh
COPY sshd_config /nix/etc/ssh/
RUN ln -s /nix/etc/ssh /etc/ssh
RUN mkdir -p /var/empty

RUN mkdir -p /setup/
COPY user.sh /setup/
RUN chmod +x /setup/*.sh && /setup/user.sh

COPY launch.sh run.sh /launch/
RUN chmod +x /launch/*.sh

WORKDIR /launch
ENTRYPOINT /launch/launch.sh
