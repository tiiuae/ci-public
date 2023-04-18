#!/bin/sh

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# Container entry point

service jenkins start
sleep 10
if [ -f /jenkins/secrets/initialAdminPassword ] ; then
  echo -n "Initial password: "
  cat /jenkins/secrets/initialAdminPassword
  rm /jenkins/secrets/initialAdminPassword
fi
/bin/sh
