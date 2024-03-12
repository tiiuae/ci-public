# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container for the hydra

FROM nixos/nix:2.20.5

RUN mkdir -p /setup/

# nix channel setup
ARG CHANNEL
COPY channel.sh /setup/
RUN chmod +x /setup/channel.sh
RUN /setup/channel.sh "$CHANNEL"

# install nix packages
RUN nix-env -i hydra -i postgresql -i jq -i gnused -i python3 -i xz

# setup users and hydra
ARG HYDRA_UID
ARG HYDRA_GID
ARG HYDRA_REMOTE_BUILDERS
ARG HYDRA_SUBSTITUTES
ARG PB_SRV
ARG HYDRA_URL

COPY user.sh nix_conf.sh hydra_conf.sh upload.sh pbhook.sh sign.sh /setup/
RUN chmod +x /setup/*.sh
RUN /setup/user.sh "$HYDRA_UID" "$HYDRA_GID" && \
    /setup/nix_conf.sh "$HYDRA_REMOTE_BUILDERS" && \
    /setup/hydra_conf.sh "$PB_SRV" "$HYDRA_URL" "$HYDRA_SUBSTITUTES"

RUN mkdir -p /run/postgresql && chmod go+w /run/postgresql
COPY launch.sh run.sh /launch/
RUN chmod +x /launch/*.sh
RUN chown -R hydra:hydra /nix/var/nix
RUN rm -Rf /root/.cache

# install sbomnix
COPY install-sbomnix.sh /setup/
RUN chmod +x /setup/install-sbomnix.sh
RUN /setup/install-sbomnix.sh

# copy all other setup scripts that will be used later
COPY postgres.sh hydra.sh populate.sh packages.lst postbuild.py cachecopy.sh \
    schedule.sh messager.py provenance.sh provenance.py \
    compress_outputs.sh webupload.sh \
    /setup/

# Fetch sha256tree.py from repo
RUN wget -O /setup/sha256tree.py https://raw.githubusercontent.com/tiiuae/ci-public/4c8d84fff191361c303605b2fa7a64961cba82c8/sha256tree/sha256tree.py

# make sure everything is executable
RUN chmod +x /setup/*.sh
RUN chmod +x /setup/messager.py
RUN chmod +x /setup/provenance.py

ARG CI_COMMIT_HASH
RUN echo "${CI_COMMIT_HASH}" > /setup/ci-version

USER hydra

WORKDIR /launch
ENTRYPOINT /launch/launch.sh
