<!--
    Copyright 2022-2024 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Containers

Follow the instructions below to run various services inside Docker containers.

## Hydra Container

### Running Hydra in Container

Custom configuration can be set with the `confs/hydra.local`.
See the default configuration in [confs/hydra.default](confs/hydra.default).

For more detailed information on configuring and running the Hydra instance, see [README.hydra](README.hydra).

The example of configuring Hydra to run on port 3001 and creating a store in the home directory:
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
The store gets initialized with the first run of the container.
When the first run exits, you can start the Hydra instance inside the container again.

To run Hydra as a service inside the container:
```
./run_hydra.sh
```
Or to run the container in the background:
```
./run_hydra.sh &
```

While the container is running, access Hydra by browsing to http://localhost:3001.

### Updating and Testing Hydra Container

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

Custom configuration can be set with `confs/bcache.local`.
See the default configuration in [confs/bcache.default](confs/bcache.default).

To build a binary cache image:
```
./build_bcache.sh
```

To run the binary cache container:
```
./buid_bcache.sh [cache directory]
```

The first run (cache-directory not existing) initializes the system.

To grant access for Hydra to upload the binary cache, add the public key of the Hydra user to the authorized keys in `{CACHE}/home/.ssh/authorized_keys`.

## Jenkins Controller Container

Custom configuration can be set with `confs/jenkins_controller.local`.
See the default configuration in [confs/jenkins_controller.default](confs/jenkins_controller.default).

To build a Jenkins controller image:
```
./build_jenkins_controller.sh
```

To run the Jenkins controller in a container:
```
./run_jenkins_controller.sh
```

The external store gets initialized at the first container run.

While the container is running, access Jenkins by browsing to http://localhost:8081.

For more detailed information on configuring and running the Jenkins controller inside a container, see [README.jcontrol](README.jcontrol).

## Jenkins Agent Container

Custom configuration can be set with `confs/jenkins_agent.local`.
See the default configuration in [confs/jenkins_agent.default](confs/jenkins_agent.default).

To build a Jenkins agent image:
```
./build_jenkins_agent.sh
```

To run the Jenkins agent in a container:
```
./run_jenkins_agent.sh
```

The external store gets initialized at the first container run.

For more detailed information on configuring and running the Jenkins agent inside a container, see [README.jagent](README.jagent).
