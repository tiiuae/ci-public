# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container for the hydra

FROM nixos/nix

RUN mkdir -p /setup/

# nix channel setup
ARG CHANNEL
COPY channel.sh /setup/
RUN chmod +x /setup/channel.sh
RUN /setup/channel.sh "$CHANNEL"

# install nix packages
RUN nix-env -i hydra -i postgresql -i jq -i gnused -i python3

# setup users and hydra
ARG HYDRA_UID
ARG HYDRA_GID
ARG HYDRA_REMOTE_BUILDERS
ARG PB_SRV
ARG HYDRA_URL

COPY user.sh nix_conf.sh hydra_conf.sh upload.sh pbhook.sh sign.sh /setup/
RUN chmod +x /setup/*.sh
RUN /setup/user.sh "$HYDRA_UID" "$HYDRA_GID" && \
    /setup/nix_conf.sh "$HYDRA_REMOTE_BUILDERS" && \
    /setup/hydra_conf.sh "$PB_SRV" "$HYDRA_URL"

RUN mkdir -p /run/postgresql && chmod go+w /run/postgresql
COPY launch.sh run.sh /launch/
RUN chmod +x /launch/*.sh
RUN chown -R hydra:hydra /nix/var/nix
RUN rm -Rf /root/.cache

# copy all other setup scripts that will be used later
COPY postgres.sh hydra.sh populate.sh packages.lst postbuild.py extracopy.sh \ 
    schedule.sh messager.py provenance.sh provenance.py \
    /setup/

# make sure everything is executable
RUN chmod +x /setup/*.sh
RUN chmod +x /setup/messager.py

ARG CONTAINER_DEBUG=false
RUN touch /etc/container-debug-${CONTAINER_DEBUG}

USER hydra

WORKDIR /launch
ENTRYPOINT /launch/launch.sh
