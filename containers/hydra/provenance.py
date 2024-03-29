#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.requests ])"

# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------

"""Script for generating SLSA compliant provenance file from hydra postbuild"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from typing import Optional

import requests

CI_REPO_URL = "https://github.com/tiiuae/ci-public"
SLSA_VERSION = "v1.0"
SLSA_LEVEL = "L2"

HYDRA_PUBLIC_URL = os.environ.get("HYDRA_URL", "http://localhost:3000").rstrip("/")
HYDRA_NAME = os.environ.get("HYDRA_NAME", "UNKNOWN")

BUILD_TYPE_PATH = (
    "{ci_repo_url}/blob/{hash}/slsa/{slsa_version}/{slsa_level}/buildtype.md"
)
BUILD_ID_PATH = "{hydra_public_url}/build/{build_id}"


def hydra_api(server: str, path: str) -> dict | None:
    """GET json data from our hydra instance"""
    if server is None:
        return None

    response = requests.get(
        server + path,
        headers={"Content-Type": "application/json"},
        timeout=30,
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


def parse_subjects(products: list[dict]) -> list[dict]:
    """return given outputs as ResourceDescriptors"""
    subjects = []
    for product in products:
        subjects += [
            {
                "name": product["name"],
                "uri": product["path"],
                "digest": {
                    "sha256": nix_hash(product["path"]),
                },
            }
        ]

    if not subjects:
        print("Warning: no subjects in provenance")

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
                "uri": CI_REPO_URL,
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
        "subject": parse_subjects(build_info["products"]),
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": BUILD_TYPE_PATH.format(
                    ci_repo_url=CI_REPO_URL,
                    hash=ci_version,
                    slsa_version=SLSA_VERSION,
                    slsa_level=SLSA_LEVEL,
                ),
                "externalParameters": {
                    "FlakeURI": flake_uri(hydra_url, build_info["build"]),
                    "target": build_info["job"],
                },
                "internalParameters": {
                    "server": HYDRA_NAME,
                    "system": build_info["system"],
                    "project": build_info["project"],
                    "jobset": build_info["jobset"],
                    "drvPath": build_info["drvPath"],
                    "release": build_info["nixName"],
                    "description": build_info["description"],
                },
                "resolvedDependencies": resolve_build_dependencies(sbom_path),
            },
            "runDetails": {
                "builder": {
                    "id": BUILD_ID_PATH.format(
                        hydra_public_url=HYDRA_PUBLIC_URL,
                        build_id=build_info["build"],
                    ),
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
    parser.add_argument("--ci-version", default="main")
    parser.add_argument("--hydra-url")
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
