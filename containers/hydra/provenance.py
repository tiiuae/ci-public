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


def parse_subjects(products: list[dict]) -> list[dict]:
    """Parse the given product path for image files
    and return them as ResourceDescriptors"""
    # TODO: use imagePath instead of products for this
    subjects = []
    for product in products:
        output_store = product["path"]
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
    """Parse the sbom for dependencies
    and return them as ResourceDescriptors"""
    if sbom_path is None:
        return []

    try:
        with open(sbom_path, "rb") as file:
            sbom = json.load(file)
    except FileNotFoundError as e:
        print(e)
        return []

    return [
        {
            "name": component["name"],
            "uri": component["bom-ref"],
        }
        for component in sbom["components"]
    ]


def list_byproducts(resultsdir: str | None):
    """Generate ResourceDescriptor for each file in the result directory
    as these files can be classified as byproducts of the build"""
    if resultsdir is None:
        return []

    return [
        {
            "name": file.rsplit("/")[-1],
            "uri": file,
        }
        for file in glob.glob(resultsdir + "/*", recursive=True)
    ]


def builder_git_rev(workspace: str | None):
    """Get git remote url and current commit hash of the build system"""
    # TODO: make this use git commit id provided by container build
    if workspace is None:
        return []

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
    build_info_path: str,
    byproduct_dir: str,
    sbom_path: Optional[str],
    builder_workspace: Optional[str],
):
    """Generate the provenance file from given inputs"""
    with open(build_info_path, "rb") as file:
        build_info = json.load(file)

    build_id = build_info["build"]
    schema = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": parse_subjects(build_info["products"]),
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": BUILD_TYPE_DOCUMENT,
                "externalParameters": {},
                "internalParameters": {
                    "system": build_info["system"],
                    "jobset": build_info["jobset"],
                    "project": build_info["project"],
                    "job": build_info["job"],
                    "drvPath": build_info["drvPath"],
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
                        build_info["startTime"],
                    ).isoformat(),
                    "finishedOn": datetime.fromtimestamp(
                        build_info["stopTime"],
                    ).isoformat(),
                },
                "byproducts": list_byproducts(byproduct_dir),
            },
        },
        "hydra_buildInfo": build_info
    }

    return schema


def main():
    """Main function that parses the given arguments"""
    parser = argparse.ArgumentParser(
        prog="Provenance Converter",
        description="Convert hydra build_info into provenance SLSA 1.0",
    )
    parser.add_argument("build_info")
    parser.add_argument("--sbom")
    parser.add_argument("--byproduct-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--builder-workspace")
    args = parser.parse_args()
    schema = generate_provenance(
        args.build_info,
        args.byproduct_dir,
        args.sbom,
        args.builder_workspace,
    )

    build_id = schema["predicate"]["runDetails"]["metadata"]["invocationId"]
    outpath = ""
    if args.output_dir:
        outpath = args.output_dir
        if not args.output_dir.endswith("/"):
            outpath += "/"

    with open(
        f"{outpath}slsa_provenance_{build_id}.json",
        "w",
        encoding="utf=8",
    ) as file:
        file.write(json.dumps(schema, indent=4))


if __name__ == "__main__":
    main()
