# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------

"""Script for generating SLSA compliant provenance file from hydra postbuild"""

import argparse
import glob
import json
import os
import subprocess
from datetime import datetime
from typing import Optional

BUILD_TYPE_DOCUMENT = "TODO"
BUILD_ID_DOCUMENT = "TODO"


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


def parse_subjects(output_store_paths: list[str]) -> list[dict]:
    """Parse the given output store path for built image files
    and return them as ResourceDescriptors"""
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


def resolve_build_dependencies(sbom_path: str | None):
    """Parse the sbom for dependencie
    and return them as ResourceDescriptors"""
    if sbom_path is None:
        return []

    with open(sbom_path, "rb") as file:
        sbom = json.load(file)
    return [
        {
            "name": component["name"],
            "uri": component["bom-ref"],
        }
        for component in sbom["components"]
    ]


def list_byproducts(resultsdir: str):
    """Generate ResourceDescriptor for each file in the result directory
    as these files can be classified as byproducts of the build"""
    return [
        {
            "name": file.rsplit("/")[-1],
            "uri": file,
        }
        for file in glob.glob(resultsdir + "/*", recursive=True)
    ]


def builder_git_rev(workspace: str | None):
    """Get git remote url and current commit hash of the build system"""
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


def generate_provenance(
    post_build_path: str,
    build_info_path: Optional[str],
    resultsdir: str,
    sbom_path: Optional[str],
    builder_workspace: Optional[str],
):
    """Generate the provenance file from given inputs"""
    with open(post_build_path, "rb") as file:
        post_build = json.load(file)

    with open(build_info_path or post_build["Postbuild info"], "rb") as file:
        build_info = json.load(file)

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
                    "project": post_build["Project"],
                    "jobset": post_build["Jobset"],
                    "job": post_build["Job"],
                    "drvPath": post_build["Derivation store path"],
                    "system": post_build["System"],
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
                "byproducts": list_byproducts(resultsdir),
            },
        },
        "hydra_buildInfo": build_info
    }

    with open(
        f"{resultsdir}/slsa_provenance_{build_id}.json",
        "w",
        encoding="utf=8",
    ) as file:
        file.write(json.dumps(schema, indent=4))


def main():
    """Main function that parses the given arguments"""
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
