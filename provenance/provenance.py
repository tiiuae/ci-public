# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
# Script for generating SLSA compliant provenance file from hydra postbuild

import argparse
import glob
import json
import os
import subprocess
from datetime import datetime
from typing import Optional


# ------------------------------------------------------------------------
# Run shell command as subprocess and get the stdout as string
# ------------------------------------------------------------------------
def run_command(cmd: list[str], **kwargs):
    out, err = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        **kwargs,
    ).communicate()
    return out.decode().strip()


# ------------------------------------------------------------------------
# Get sha256 hash of nix store item
# ------------------------------------------------------------------------
def nix_hash(image: str):
    return run_command(["nix-hash", "--base32", "--type", "sha256", image])


# ------------------------------------------------------------------------
# Parse the given output store path for built image files
# and return them as ResourceDescriptors
# ------------------------------------------------------------------------
def parse_subjects(output_store_paths: list[str]) -> list[dict]:
    subjects = []
    for output_store in output_store_paths:
        if os.path.exists(output_store):
            subjects += [
                {
                    "name": file,
                    "uri": f"{output_store}/{file}",
                    "digest": {
                        "sha256": nix_hash(f"{output_store}/{file}"),
                    },
                }
                for file in os.listdir(output_store)
            ]
        else:
            # built image is not available, create best effort subject
            subjects.append({"uri": output_store})

    return subjects


# ------------------------------------------------------------------------
# Parse the sbom for dependencies and return them as ResourceDescriptors
# ------------------------------------------------------------------------
def resolve_build_dependencies(sbom_path: str | None):
    if sbom_path is None:
        return []

    with open(sbom_path, "rb") as f:
        sbom = json.load(f)
    return [
        {
            "name": component["name"],
            "uri": component["bom-ref"],
        }
        for component in sbom["components"]
    ]


# ------------------------------------------------------------------------
# Generate ResourceDescriptor for each file in the result directory
# as these files can be classified as byproducts of the build
# ------------------------------------------------------------------------
def list_byproducts(resultsdir: str):
    return [
        {
            "name": file.rsplit("/")[-1],
            "uri": file,
        }
        for file in glob.glob(resultsdir + "/*", recursive=True)
    ]


# ------------------------------------------------------------------------
# Get git remote url and current commit hash of the build system
# ------------------------------------------------------------------------
def builder_git_rev(workspace: str | None):
    url = run_command(
        ["git", "remote", "get-url", "origin"],
        cwd=workspace,
    )
    commit_hash = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
    )

    return [
        {
            "uri": url,
            "digest": {
                "gitCommit": commit_hash,
            },
        }
    ]


# ------------------------------------------------------------------------
# Generate the provenance file from given inputs
# ------------------------------------------------------------------------
def generate_provenance(
    post_build_path: str,
    build_info_path: Optional[str],
    resultsdir: str,
    sbom_path: Optional[str],
    builder_workspace: Optional[str],
):
    with open(post_build_path, "rb") as f:
        post_build = json.load(f)

    with open(build_info_path or post_build["Postbuild info"], "rb") as f:
        build_info = json.load(f)

    BUILD_TYPE_DOCUMENT = "TODO"
    BUILD_ID_DOCUMENT = "TODO"

    build_id = post_build["Build ID"]
    schema = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": parse_subjects(post_build["Output store paths"]),
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": BUILD_TYPE_DOCUMENT,
                "externalParameters": {},
                "internalParameters": {
                    "server": post_build["Server"],
                    "system": post_build["System"],
                    "jobset": post_build["Jobset"],
                    "project": post_build["Project"],
                    "job": post_build["Job"],
                    "drvPath": post_build["Derivation store path"],
                },
                "resolvedDependencies": resolve_build_dependencies(sbom_path),
            },
            "runDetails": {
                "builder": {
                    "id": BUILD_ID_DOCUMENT,
                    "builderDependencies": builder_git_rev(builder_workspace),
                },
                "metadata": {
                    "invocationId": build_id,
                    "startedOn": datetime.fromtimestamp(
                        build_info["startTime"]
                    ).isoformat(),
                    "finishedOn": datetime.fromtimestamp(
                        build_info["stopTime"]
                    ).isoformat(),
                },
                "byproducts": [list_byproducts(resultsdir)],
            },
        },
    }

    with open(f"{resultsdir}/slsa_provenance_{build_id}.json", "w") as f:
        f.write(json.dumps(schema, indent=4))


# ------------------------------------------------------------------------
# Main function that parses the given arguments
# ------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="Provenance Converter",
        description="Convert hydra build_info into provenance SLSA 1.0",
    )
    parser.add_argument("post_build_path")
    parser.add_argument("--buildinfo")
    parser.add_argument("--sbom")
    parser.add_argument("--results-dir", default="./")
    parser.add_argument("--builder-workspace")
    args = parser.parse_args()
    generate_provenance(
        args.post_build_path,
        args.buildinfo,
        args.results_dir,
        args.sbom,
        args.builder_workspace,
    )


if __name__ == "__main__":
    main()
