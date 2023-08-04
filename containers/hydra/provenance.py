#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.requests ])"

# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------

"""Script for generating SLSA compliant provenance file from hydra postbuild"""

import argparse
import json
import subprocess
from datetime import datetime
from typing import Optional

import requests

BUILD_TYPE_PATH = "https://github.com/tiiuae/ci-public/blob/{0}/provenance/buildtype.md"
BUILD_ID_PATH = "TODO"


def hydra_api(server: str, path: str) -> dict | None:
    """GET json data from our hydra instance"""
    if server is None:
        return None

    response = requests.get(
        server + path,
        headers={"Content-Type": "application/json"},
    )
    if response.status_code == 200:
        return response.json()

    print(f"{server}{path} returned {response.status_code}")
    return None


def flake_uri(server: str, build_id: int) -> str:
    """Get the flake URI from hydra"""
    build_data = hydra_api(server, f"/build/{build_id}")
    if build_data:
        eval_data = hydra_api(server, f"/eval/{build_data['jobsetevals'][0]}")
        if eval_data:
            return eval_data["flake"]
    return None


def run_command(cmd: list[str], **kwargs):
    """Run shell command as subprocess and get the stdout as string"""
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        **kwargs,
    ) as proc:
        out, _err = proc.communicate()
        return out.decode().strip()


def nix_hash(image: str):
    """Get sha256 hash of nix store item"""
    return run_command(["nix-hash", "--base32", "--type", "sha256", image])


def parse_subjects(image_paths: list[str | None]) -> list[dict]:
    """return given images as ResourceDescriptors"""
    subjects = []
    for image in image_paths:
        if image is not None:
            subjects += [
                {
                    "name": image.rsplit("/", 1)[-1],
                    "uri": image,
                    "digest": {
                        "sha256": nix_hash(image),
                    },
                }
            ]

    return subjects


def resolve_build_dependencies(sbom: dict | None):
    """Parse the sbom for dependencies
    and return them as ResourceDescriptors"""
    if sbom is None:
        return []

    return [
        {
            "name": component["name"],
            "uri": component["bom-ref"],
        }
        for component in sbom["components"]
    ]


def builder_dependencies(commit_hash: str | None):
    """Get current version of the build system"""
    deps = []
    if commit_hash:
        deps.append(
            {
                "uri": "https://github.com/tiiuae/ci-public",
                "digest": {
                    "gitCommit": commit_hash,
                },
            }
        )

    return deps


def generate_provenance(
    build_info: dict,
    sbom_path: Optional[str],
    ci_version: Optional[str],
    hydra_url: Optional[str],
):
    """Generate the provenance file from given inputs"""
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": parse_subjects([build_info.get("imageLink")]),
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": BUILD_TYPE_PATH.format(ci_version),
                "externalParameters": {
                    "FlakeURI": flake_uri(hydra_url, build_info["build"]),
                    "target": build_info["job"],
                },
                "internalParameters": {
                    "system": build_info["system"],
                    "project": build_info["project"],
                    "jobset": build_info["jobset"],
                    "drvPath": build_info["drvPath"],
                    "release": build_info["nixName"],
                },
                "resolvedDependencies": resolve_build_dependencies(sbom_path),
            },
            "runDetails": {
                "builder": {
                    "id": BUILD_ID_PATH,
                    "builderDependencies": builder_dependencies(ci_version),
                },
                "metadata": {
                    "invocationId": build_info["build"],
                    "startedOn": datetime.fromtimestamp(
                        build_info["startTime"],
                    ).isoformat(),
                    "finishedOn": datetime.fromtimestamp(
                        build_info["stopTime"],
                    ).isoformat(),
                },
                "byproducts": [],
            },
        },
        "hydra_buildInfo": build_info,
    }


def main():
    """Main function that parses the given arguments"""
    parser = argparse.ArgumentParser(
        prog="Provenance Converter",
        description="Convert hydra build_info into provenance SLSA 1.0",
    )
    parser.add_argument("build_info")
    parser.add_argument("--sbom", type=argparse.FileType("r", encoding="UTF-8"))
    parser.add_argument("--out", type=argparse.FileType("w", encoding="UTF-8"))
    parser.add_argument("--ci-version")
    parser.add_argument("--hydra-url", default="http://localhost:3000")
    args = parser.parse_args()

    with open(args.build_info, "rb") as file:
        build_info = json.load(file)

    sbom = json.load(args.sbom) if args.sbom else None
    schema = generate_provenance(build_info, sbom, args.ci_version, args.hydra_url)

    if args.out:
        args.out.write(json.dumps(schema, indent=4))
    else:
        print(json.dumps(schema, indent=4))


if __name__ == "__main__":
    main()
