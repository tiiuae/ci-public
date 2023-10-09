#!/usr/bin/env pipenv-shebang
"""
------------------------------------------------------------------------
SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
SPDX-License-Identifier: Apache-2.0
------------------------------------------------------------------------

Hydra post build hook script

------------------------------------------------------------------------
"""

import json
import os
import sys

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------
ENCOD = "UTF-8"
JSONFN = None
HYDRA = None
MESSAGE_SCRIPT = None
PROVENANCE_SCRIPT = None
PACKAGE_SCRIPT = None


# ------------------------------------------------------------------------
def perror(txt, code=1):
    """
    Prints an error message and exits
    txt = Error message
    code = optional exit code
    """

    if txt is not None:
        print(txt, file=sys.stderr)

    if MESSAGE_SCRIPT is not None:
        ret = os.system(MESSAGE_SCRIPT)
        if ret != 0:
            print(f"Message script return code: {ret}", file=sys.stderr)

    sys.exit(code)


# ------------------------------------------------------------------------
def run_script(script: str, exit_on_fail: bool = False) -> int:
    """Run given script"""
    ret = 0
    if script is not None:
        ret = os.system(script)
        if ret != 0:
            print(f"{script} failed: {ret}", file=sys.stderr)
            if exit_on_fail:
                sys.exit(1)
    return ret


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

    # copy output and derivation to the cache
    run_script(f"/setup/upload.sh {outp} {binfo['drvPath']}", exit_on_fail=True)

    run_script(PROVENANCE_SCRIPT)
    run_script(PACKAGE_SCRIPT)

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

    # Get message script if available
    MESSAGE_SCRIPT = os.getenv("POSTBUILD_MESSAGE_SCRIPT")

    # Get provenance script if available
    PROVENANCE_SCRIPT = os.getenv("POSTBUILD_PROVENANCE_SCRIPT")

    # Get packaging script if available
    PACKAGE_SCRIPT = os.getenv("POSTBUILD_PACKAGE_SCRIPT")

    main()
