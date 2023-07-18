# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container for the hydra

FROM nixos/nix

RUN mkdir -p /setup/
COPY channel.sh user.sh nix_conf.sh postgres.sh hydra.sh \
     populate.sh packages.lst /setup/
COPY hydra_conf.sh postbuild.py messager.py extracopy.sh schedule.sh /setup/

RUN mkdir -p /home/hydra/scripts
COPY pbhook.sh upload.sh sign.sh /home/hydra/scripts/

RUN chmod +x /setup/*.sh /home/hydra/scripts/*.sh

ARG CHANNEL
RUN /setup/channel.sh "$CHANNEL"

ARG HYDRA_UID
ARG HYDRA_GID
ARG HYDRA_REMOTE_BUILDERS
ARG PB_SRV
ARG HYDRA_URL

RUN nix-env -i hydra -i postgresql -i jq -i gnused

RUN /setup/user.sh "$HYDRA_UID" "$HYDRA_GID" && \
    /setup/nix_conf.sh "$HYDRA_REMOTE_BUILDERS" && \
    /setup/hydra_conf.sh "$PB_SRV" "$HYDRA_URL"

RUN mkdir -p /run/postgresql && chmod go+w /run/postgresql
COPY launch.sh run.sh /launch/
RUN chmod +x /launch/*.sh
RUN chown -R hydra:hydra /nix/var/nix
RUN rm -Rf /root/.cache

ARG CONTAINER_DEBUG=false
RUN touch /etc/container-debug-${CONTAINER_DEBUG}

USER hydra

WORKDIR /launch
ENTRYPOINT /launch/launch.sh
