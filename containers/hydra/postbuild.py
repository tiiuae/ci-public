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
import sys
import json
import os
import tempfile
import subprocess


# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------
imagefn = "nixos.img"
nixstore = "nix-store"
linksuffix = "-nixos.img"
infosuffix = "-build-info.json"


# ------------------------------------------------------------------------
# Prints an error message and exits
# txt = Error message
# code = optional exit code
# ------------------------------------------------------------------------
def perror(txt, code=1):
    if txt != None:
        print(txt, file=sys.stderr)

    messagescript = os.getenv("POSTBUILD_MSGSCRIPT")
    if messagescript != None:
        ret = os.system(messagescript)
        if ret != 0:
            print(f"Message script return code: {ret}", file=sys.stderr)

    sys.exit(code)

# ------------------------------------------------------------------------
# Add given path to nix store
# path = path to file/dir to be added
# returns nix store path for added file/dir
# ------------------------------------------------------------------------
def nix_store_add(path: str) -> str:
    result = subprocess.run([nixstore, '--add', path], stdout=subprocess.PIPE)

    if result.returncode != 0:
        perror(f"{nixstore} --add {path} failed ({result.returncode}):\n{result.stderr.decode('utf-8')}")

    return result.stdout.decode('utf-8').strip()


# ------------------------------------------------------------------------
# Remove given path from nix store (if it exists, no error if nonexistent)
# path = nix store path to remove
# ------------------------------------------------------------------------
def nix_store_del(path: str):
    if os.path.exists(path):
        result = subprocess.run([nixstore, '--delete', path], stdout=subprocess.PIPE)

        if result.returncode != 0:
            perror(f"{nixstore} --delete {path} failed ({result.returncode}):\n{result.stderr.decode('utf-8')}")


# ------------------------------------------------------------------------
# Main program
# ------------------------------------------------------------------------
def main(argv: list[str]):
    # Declare as globals just in case
    global imagefn
    global nixstore
    global linksuffix
    global infosuffix

    # HYDRA_JSON is set by Hydra to point to build information .json file
    jsonfn = os.getenv("HYDRA_JSON")
    if jsonfn == None:
        perror("HYDRA_JSON not defined")

    # POSTBUILD_SERVER needs to be set to the current server (e.g. hydra or awsarm)
    hydra = os.getenv("POSTBUILD_SERVER")
    if hydra == None:
        perror("POSTBUILD_SERVER not defined")

    # Allow override of the default nix-store command
    nixstore = os.getenv("POSTBUILD_NIXSTORE", nixstore)

    # Allow override of the default image file name
    imagefn = os.getenv("POSTBUILD_IMAGE", imagefn)

    # Allow override of the default image link suffix
    linksuffix = os.getenv("POSTBUILD_LINKSUFFIX", linksuffix)

    # Allow override of the default info file suffix
    infosuffix = os.getenv("POSTBUILD_INFOSUFFIX", infosuffix)

    # Load build information
    with open(jsonfn) as jsonf:
        binfo = json.load(jsonf)

    # Check status of the build, we are interested only in finished builds
    if binfo['buildStatus'] != 0 or binfo['finished'] != True or binfo['event'] != "buildFinished":
        perror("Unexpected build status")

    # Find output path
    outp = None
    for output in binfo['outputs']:
        if output['name'] == 'out':
            outp = output['path']

    if outp == None:
        perror("Output not found")

    imgf = outp + "/" + imagefn

    # Check that output image file exists
    if not os.path.isfile(imgf):
        perror(f"{imgf} not found")

    target = binfo['job'].split('.')[0]
    build = binfo['build']
    linkname = f"{target}{linksuffix}"
    infoname = f"{hydra}-{build}{infosuffix}"

    # Create link and info file in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        linkfn = f"{tmpdir}/{linkname}"
        infofn = f"{tmpdir}/{infoname}"

        # Create symlink to image and add it to nix store
        os.symlink(imgf, linkfn)
        niximglink = nix_store_add(linkfn)

        print(f'POSTBUILD_LINK="{niximglink}"')

        # Add symlink info also to build information
        binfo['imageLink'] = niximglink

        # Write build information to build info file and add to nix store
        with open(infofn, "w") as infof:
            json.dump(binfo, infof)

        nixbuildinfo = nix_store_add(infofn)

        subprocess.run(["/setup/sign.sh", nixbuildinfo]);

        # Print the build-info nix store path so that it can be scraped
        # from Hydra web ui run command logs automatically.
        print(f'POSTBUILD_INFO="{nixbuildinfo}"')

    perror(None, 0)


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv)
