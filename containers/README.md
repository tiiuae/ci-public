<!--
    Copyright 2023 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Containers

Follow the instructions below to run various services inside Docker containers.

## Hydra Container

### Run Hydra in Container

Custom configuration can be set with the `confs/hydra.local`.
See the default configuration in the [confs/hydra.default](confs/hydra.default).

[More detailed instructions to configure and run the Hydra instance](README.hydra)

Here is an example for configuring Hydra to run on port 3001 and creating a store in the home directory:
```
HC_PORT=3001

HC_BASE_LABEL="hydra-container"
HC_PB_SRV="hydra"

HC_STORE_PATH=/home/$USER/store

PW_ADMIN="changeme"
PW_AUTO="changeme"

HC_CUSTOM_HOSTS=()
```

Build the Hydra image and create the store:
```
./build_hydra.sh
./run_hydra.sh
```
The store gets initialized with the first run of container. When the first run have exited, you can start Hydra instance inside the container again.

To run Hydra as a service inside the container:
```
./run_hydra.sh
```
Or to run the container in the background :
```
./run_hydra.sh &
```

While the container is running, access Hydra by browsing to http://localhost:3001.

### Update and Test Hydra Container

Stop and remove the container named as `hydra-container`:
```
docker stop hydra-container
docker rm hydra-container
```

Make your changes and test them:
```
./build_hydra.sh
./run_hydra.sh
```

## Binary Cache Container

Custom configuration can be set with the `confs/bcache.local`.
See the default configuration in the [confs/bcache.default](confs/bcache.default).

To build a binary cache image:
```
./build_bcache.sh
```

To run the binary cache container:
```
./buid_bcache.sh [cache directory]
```

First run (cache-directory not existing) initializes the system.

To grant access for Hydra to upload the binary cache, add the public key of the Hydra user to the authorized keys in `{CACHE}/home/.ssh/authorized_keys`.

## Jenkins Controller Container

Custom configuration can be set with the `confs/jenkins_controller.local`.
See the default configuration in the [confs/jenkins_controller.default](confs/jenkins_controller.default).

To build a Jenkins controller image:
```
./build_jenkins_controller.sh
```

To run the Jenkins controller in a container:
```
./run_jenkins_controller.sh
```

External store gets initialized at the first container run.

While the container is running, access Jenkins by browsing to http://localhost:8081.

[More detailed instructions to configure and run the Jenkins controller inside a container](README.jcontrol)

## Jenkins Agent Container

Custom configuration can be set with the `confs/jenkins_agent.local`.
See the default configuration in the [confs/jenkins_agent.default](confs/jenkins_agent.default).

To build a Jenkins agent image:
```
./build_jenkins_agent.sh
```

To run the Jenkins agent in a container:
```
./run_jenkins_agent.sh
```

External store gets initialized at the first container run.

[More detailed instructions to configure and run the Jenkins agent inside a container](README.jagent)