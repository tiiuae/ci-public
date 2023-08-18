#!/usr/bin/env pipenv-shebang
"""
------------------------------------------------------------------------
SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
SPDX-License-Identifier: Apache-2.0
------------------------------------------------------------------------

Hydra post build hook script

Creates build information json file and a symbolic link to the image file
with human understandable name.
------------------------------------------------------------------------
"""

import json
import os
import subprocess
import sys
import tempfile

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------
IMAGEFN = "nixos.img"
NIXSTORE = "nix-store"
LINKSUFFIX = "-nixos.img"
INFOSUFFIX = "-build-info.json"
PROVENANCESUFFIX = "-provenance.json"
ENCOD = "UTF-8"
JSONFN = None
HYDRA = None
MESSAGESCRIPT = None


# ------------------------------------------------------------------------
def perror(txt, code=1):
    """
    Prints an error message and exits
    txt = Error message
    code = optional exit code
    """

    if txt is not None:
        print(txt, file=sys.stderr)

    if MESSAGESCRIPT is not None:
        ret = os.system(MESSAGESCRIPT)
        if ret != 0:
            print(f"Message script return code: {ret}", file=sys.stderr)

    sys.exit(code)


# ------------------------------------------------------------------------
def create_signature(path: str) -> str:
    """
    Sign the given file
    path = path to file/dir to be signed
    returns nix store path of the signature
    """

    result = subprocess.run(["/setup/sign.sh", path],
                            stdout=subprocess.PIPE, check=False)

    if result.returncode != 0:
        perror(
            "sign.sh {path} failed ({result.returncode}):"
            f"\n{result.stderr.decode('utf-8')}"
        )

    return result.stdout.decode("utf-8").strip()


# ------------------------------------------------------------------------
def nix_store_add(path: str) -> str:
    """
    Add given path to nix store
    path = path to file/dir to be added
    returns nix store path for added file/dir
    """

    result = subprocess.run([NIXSTORE, "--add", path],
                            stdout=subprocess.PIPE, check=False)

    if result.returncode != 0:
        perror(
            f"{NIXSTORE} --add {path} failed ({result.returncode}):"
            f"\n{result.stderr.decode('utf-8')}"
        )

    return result.stdout.decode("utf-8").strip()


# ------------------------------------------------------------------------
def nix_store_del(path: str):
    """
    Remove given path from nix store (if it exists, no error if nonexistent)
    path = nix store path to remove
    """

    if os.path.exists(path):
        result = subprocess.run(
            [NIXSTORE, "--delete", path], stdout=subprocess.PIPE, check=False)

        if result.returncode != 0:
            perror(
                f"{NIXSTORE} --delete {path} failed ({result.returncode}):"
                f"\n{result.stderr.decode('utf-8')}"
            )


# ------------------------------------------------------------------------
def main():
    """Main program"""

    # Load build information
    with open(JSONFN, encoding=ENCOD) as jsonf:
        binfo = json.load(jsonf)

    # Check status of the build, we are interested only in finished builds
    if (
        not binfo["finished"]
        or binfo["buildStatus"] != 0
        or binfo["event"] != "buildFinished"
    ):
        perror("Unexpected build status")

    # Find output path
    outp = None
    for output in binfo["outputs"]:
        if output["name"] == "out":
            outp = output["path"]

    if outp is None:
        perror("Output not found")

    outp += "/" + IMAGEFN

    # Check that output image file exists
    if not os.path.isfile(outp):
        perror(f"{outp} is not an existing file")

    target = binfo["job"].split(".")[0]
    build = binfo["build"]

    linkname = f"{target}{LINKSUFFIX}"
    infoname = f"{HYDRA}-{build}{INFOSUFFIX}"
    provenancename = f"{HYDRA}-{build}{PROVENANCESUFFIX}"

    # Create link and info file in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        linkfn = f"{tmpdir}/{linkname}"
        infofn = f"{tmpdir}/{infoname}"

        # Create symlink to image and add it to nix store
        os.symlink(outp, linkfn)
        niximglink = nix_store_add(linkfn)
        print(f'POSTBUILD_LINK="{niximglink}"')

        # Add symlink info also to build information
        binfo["imageLink"] = niximglink

        # Write build information to build info file and add to nix store
        with open(infofn, "w", encoding=ENCOD) as infof:
            json.dump(binfo, infof)

        nixbuildinfo = nix_store_add(infofn)

        # Print the build-info nix store path so that it can be scraped
        # from Hydra web ui run command logs automatically.
        print(f'POSTBUILD_INFO="{nixbuildinfo}"')
        print(f'POSTBUILD_INFO_SIGNATURE="{create_signature(nixbuildinfo)}"')

        # generate provenance
        result = subprocess.run(
            [
                "/setup/provenance.sh",
                niximglink,  # image path
                nixbuildinfo,  # buildinfo path
                tmpdir,  # working dir for provenance and sbom
                provenancename,  # file to save the provenance to
            ],
            stdout=subprocess.PIPE,
            check=False
        )
        if result.returncode != 0:
            perror(
                f"provenance.sh failed ({result.returncode}):"
                f"\n{result.stderr.decode('utf-8')}"
            )

        # print the output of provenance.sh
        # PROVENANCE_LINK and PROVENANCE_SIGNATURE_LINK
        print(result.stdout.decode("utf-8").strip())

    perror(None, 0)


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    # HYDRA_JSON is set by Hydra to point to build information .json file
    JSONFN = os.getenv("HYDRA_JSON")
    if JSONFN is None:
        perror("HYDRA_JSON not defined")

    # POSTBUILD_SERVER needs to be set to the current server (e.g. hydra or awsarm)
    HYDRA = os.getenv("POSTBUILD_SERVER")
    if HYDRA is None:
        perror("POSTBUILD_SERVER not defined")

    # Get messagescript name if available
    MESSAGESCRIPT = os.getenv("POSTBUILD_MSGSCRIPT")

    # Allow override of the default nix-store command
    NIXSTORE = os.getenv("POSTBUILD_NIXSTORE", NIXSTORE)

    # Allow override of the default image file name
    IMAGEFN = os.getenv("POSTBUILD_IMAGE", IMAGEFN)

    # Allow override of the default image link suffix
    LINKSUFFIX = os.getenv("POSTBUILD_LINKSUFFIX", LINKSUFFIX)

    # Allow override of the default info file suffix
    INFOSUFFIX = os.getenv("POSTBUILD_INFOSUFFIX", INFOSUFFIX)

    # Allow override of the provenance file suffix
    PROVENANCESUFFIX = os.getenv(
        "POSTBUILD_PROVENANCE_SUFFIX", PROVENANCESUFFIX)

    main()
