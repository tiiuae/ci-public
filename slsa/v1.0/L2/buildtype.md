<!--
    Copyright 2022-2023 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Build Type: Hydra

## Description

This `buildType` describes the execution of hydra job that builds a software artifact.

A hydra project can have jobsets and jobset can have multiple jobs.
Hydra jobs are called evaluations.
All job parameters and jobset definitions are read from the flake path.

Read more about hydra from the [hydra manual]

[hydra manual]: https://hydra.nixos.org/build/196107287/download/1/hydra/introduction.html

## Build Definition

### External parameters

[External parameters]: #external-parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `FlakeURI`| URI | URI to the flake to be built, such as `git+https://github.com/tiiuae/ghaf/` |
| `target`  | string | The target job for this build |

### Internal parameters

All internal parameters SHOULD be present for every build.

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `system`  | string | The system the image will be built for such as `x86_64-linux` or `aarch64-linux`. |
| `project` | string | The project this jobset is a part of |
| `jobset`  | string | The jobset this evaluation is a part of |
| `drvPath` | path   | Path to the built derivation in the nix store |
| `release` | string | The release to be built such as `nixos-disk-image` or `nixos-vm`. |

### Resolved dependencies

Contains every build time dependency of the image that was built.

`uri` here refers to the path of the dependency in the nix store.

## Run details

### Builder

The `builder.id` MUST represent the entity that generated the provenance, as per
the [SLSA Provenance](https://slsa.dev/provenance/v1#builder.id) documentation.

Our `builder.id` is a link to the hydra build results page.

### byProducts

List of extra files generated during build, excluding the main image.

### Metadata

The `invocationId` SHOULD be set to the corresponding evaluation ID in hydra.
