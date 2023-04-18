# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container for the jenkins controller

FROM ubuntu:jammy

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes \
          wget gnupg

RUN wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
    > /usr/share/keyrings/jenkins-keyring.asc
RUN echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
    https://pkg.jenkins.io/debian-stable binary/ | tee \
    /etc/apt/sources.list.d/jenkins.list > /dev/null

ARG JCONTROL_UID
ARG JCONTROL_GID

COPY launch.sh /launch/
COPY user.sh /setup/
RUN chmod +x /launch/*.sh /setup/*.sh

WORKDIR /launch

RUN /setup/user.sh "$JCONTROL_UID" "$JCONTROL_GID"

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes \
          openjdk-11-jdk-headless jenkins \
    && DEBIAN_FRONTEND=noninteractive apt-get clean --yes

RUN mkdir /jenkins && \
    chmod g+w /jenkins && \
    chown "$JCONTROL_UID:jenkins" /jenkins && \
    echo "JENKINS_HOME=/jenkins" >> /etc/default/jenkins

ENTRYPOINT /launch/launch.sh
