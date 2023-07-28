#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
# Hydra post build hook script
#
# Creates build information json file and a symbolic link to the image file
# with human understandable name.
# ------------------------------------------------------------------------
import json
import os
import subprocess
import sys
import tempfile

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------
imagefn = "nixos.img"
nixstore = "nix-store"
linksuffix = "-nixos.img"
infosuffix = "-build-info.json"
provenancesuffix = "-provenance.json"


# ------------------------------------------------------------------------
# Prints an error message and exits
# txt = Error message
# code = optional exit code
# ------------------------------------------------------------------------
def perror(txt, code=1):
    if txt is not None:
        print(txt, file=sys.stderr)

    messagescript = os.getenv("POSTBUILD_MSGSCRIPT")
    if messagescript is not None:
        ret = os.system(messagescript)
        if ret != 0:
            print(f"Message script return code: {ret}", file=sys.stderr)

    if txt is not None:
        print("Quitting early")
        sys.exit(code)


# ------------------------------------------------------------------------
# Sign the given file
# path = path to file/dir to be signed
# returns nix store path of the signature
# ------------------------------------------------------------------------
def create_signature(path: str) -> str:
    result = subprocess.run(["/setup/sign.sh", path], stdout=subprocess.PIPE)

    if result.returncode != 0:
        perror(
            "sign.sh {path} failed ({result.returncode}):"
            f"\n{result.stderr.decode('utf-8')}"
        )

    return result.stdout.decode("utf-8").strip()


# ------------------------------------------------------------------------
# Add given path to nix store
# path = path to file/dir to be added
# returns nix store path for added file/dir
# ------------------------------------------------------------------------
def nix_store_add(path: str) -> str:
    result = subprocess.run([nixstore, "--add", path], stdout=subprocess.PIPE)

    if result.returncode != 0:
        perror(
            f"{nixstore} --add {path} failed ({result.returncode}):"
            f"\n{result.stderr.decode('utf-8')}"
        )

    return result.stdout.decode("utf-8").strip()


# ------------------------------------------------------------------------
# Remove given path from nix store (if it exists, no error if nonexistent)
# path = nix store path to remove
# ------------------------------------------------------------------------
def nix_store_del(path: str):
    if os.path.exists(path):
        result = subprocess.run([nixstore, "--delete", path], stdout=subprocess.PIPE)

        if result.returncode != 0:
            perror(
                f"{nixstore} --delete {path} failed ({result.returncode}):"
                f"\n{result.stderr.decode('utf-8')}"
            )


# ------------------------------------------------------------------------
# Main program
# ------------------------------------------------------------------------
def main(argv: list[str]):
    # Declare as globals just in case
    global imagefn
    global nixstore
    global linksuffix
    global infosuffix
    global provenancesuffix

    # HYDRA_JSON is set by Hydra to point to build information .json file
    jsonfn = os.getenv("HYDRA_JSON")
    if jsonfn is None:
        perror("HYDRA_JSON not defined")

    # POSTBUILD_SERVER needs to be set to the current server (e.g. hydra or awsarm)
    hydra = os.getenv("POSTBUILD_SERVER")
    if hydra is None:
        perror("POSTBUILD_SERVER not defined")

    # Allow override of the default nix-store command
    nixstore = os.getenv("POSTBUILD_NIXSTORE", nixstore)

    # Allow override of the default image file name
    imagefn = os.getenv("POSTBUILD_IMAGE", imagefn)

    # Allow override of the default image link suffix
    linksuffix = os.getenv("POSTBUILD_LINKSUFFIX", linksuffix)

    # Allow override of the default info file suffix
    infosuffix = os.getenv("POSTBUILD_INFOSUFFIX", infosuffix)
    
    # Allow override of the provenance file suffix
    provenancesuffix = os.getenv("POSTBUILD_PROVENANCE_SUFFIX", provenancesuffix)

    # Load build information
    with open(jsonfn) as jsonf:
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

    imgf = outp + "/" + imagefn

    # Check that output image file exists
    if not os.path.isfile(imgf):
        perror(f"{imgf} not found")

    target = binfo["job"].split(".")[0]
    build = binfo["build"]

    linkname = f"{target}{linksuffix}"
    infoname = f"{hydra}-{build}{infosuffix}"
    provenancename = f"{hydra}-{build}{provenancesuffix}"

    # Create link and info file in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        linkfn = f"{tmpdir}/{linkname}"
        infofn = f"{tmpdir}/{infoname}"

        # Create symlink to image and add it to nix store
        os.symlink(imgf, linkfn)
        niximglink = nix_store_add(linkfn)
        print(f'POSTBUILD_LINK="{niximglink}"')

        # Add symlink info also to build information
        binfo["imageLink"] = niximglink

        # Write build information to build info file and add to nix store
        with open(infofn, "w") as infof:
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
    main(sys.argv)
