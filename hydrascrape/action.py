#!/usr/bin/env pipenv-shebang
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
"""
Action script for hydra scraper
"""
import json
import os
import re
import subprocess
import sys


def perror(txt, code=1):
    """Prints an error message and exits

    @param txt: Error message
    @param code: optional exit code
    """
    print(txt, file=sys.stderr)
    sys.exit(code)


def nix_copy(
    cacheurl: str,
    paths: list[str],
    derivation: bool = False,
    refresh: bool = False,
):
    """Copies stuff from cache"""
    if len(paths) < 1:
        return

    if refresh:
        refreshcmd = ["nix", "path-info", "--refresh", "--store", cacheurl]
        refreshcmd.extend(paths)
        subprocess.run(refreshcmd, stdout=subprocess.PIPE, check=False)

    nixcopy = ["nix", "copy", "--from", cacheurl]
    if derivation:
        nixcopy.insert(2, "--derivation")

    nixcopy.extend(paths)

    result = subprocess.run(nixcopy, stdout=subprocess.PIPE, check=False)
    if result.returncode != 0:
        perror(result.stderr, result.returncode)


def get_outputs(iout: list[dict] | None) -> list:
    """Convert hydra json style outputs to plain list of paths

    @param iout: outputs list in hydra json style

    @return: list of paths (maybe empty)
    """
    oout = []
    if iout is not None:
        for output in iout:
            outp = output.get("path")
            if outp is not None:
                oout.append(outp)
    return oout


# Translate table for json items, used by translate function
transtable = {
    "build": "Build ID",
    "system": "System",
    "nixName": "Nix name",
    "timestamp": "Queued at",
    "startTime": "Build started",
    "stopTime": "Build finished",
    "drvPath": "Derivation store path",
    "job": "Job",
    "project": "Project",
    "jobset": "Jobset",
    "homepage": "Homepage",
    "description": "Short description",
    "license": "License",
}


def translate(ibinfo: dict, obinfo: dict):
    """Translate hydra post build json to more readable (scraped-like) json

    @param ibinfo: dictionary containing hydra post build json
    @param obinfo: dictionary containing scraped values.
                   values overwritten or appended, may be empty
    """
    for old_name, new_name in transtable.items():
        val = ibinfo.get(old_name)
        if val is not None:
            # Convert all to strings
            val = str(val)
            oval = obinfo.get(new_name)
            # Check and warn if there's contradicting info
            if oval is not None and oval != val:
                print("Warning! differing build information:", file=sys.stderr)
                print(f"  {old_name} = {val}", file=sys.stderr)
                print(f"  {new_name} = {oval}", file=sys.stderr)
            # Trust the nix-store json file rather than scraped stuff
            obinfo[new_name] = val

    # Handle outputs separately
    ooutputs = get_outputs(ibinfo.get("outputs"))

    # Check outputs also
    obio = obinfo.get("Output store paths")
    if obio is not None and obio != ooutputs:
        print("Warning! differing build information:", file=sys.stderr)
        print(f"  outputs = {ooutputs}", file=sys.stderr)
        print(f"  Output store paths = {obio}", file=sys.stderr)

    obinfo["Output store paths"] = ooutputs


def min_info_from_env() -> dict:
    """Get minimal build info from environment variables
    (Rest should be in post build json file)

    @return: dictionary of build info
    """
    envl = ["Server", "Postbuild info", "Maintainers", "Closure size", "Output size"]
    res = {}

    for name in envl:
        env_value = os.getenv(f"HYDRA_{name.upper().replace(' ','_')}")
        if env_value is not None:
            res[name] = env_value
    return res


def main():
    """Main function"""
    cacheurl = "https://cache.vedenemo.dev"
    wlist = "wlist.txt"

    # Allow cache url override
    cacheurl = os.getenv("ACTION_CACHEURL", cacheurl)

    # Allow wlist file name override
    wlist = os.getenv("ACTION_WLISTFILE", wlist)

    bnum = os.getenv("HYDRA_BUILD_ID")
    if bnum is None:
        perror("Error: HYDRA_BUILD_ID not defined", 0)

    print(f"Hydra Build ID: {bnum}")

    provenance_file = os.getenv("HYDRA_PROVENANCE_FILE")
    if provenance_file is None:
        perror("Error: HYDRA_PROVENANCE_FILE not defined", 0)

    outputs = []
    for key, value in os.environ.items():
        if key.startswith("HYDRA_POSTBUILD_PACKAGE_OUTPUT_PATH_"):
            index = int(key[-1])
            signature = os.getenv(f"HYDRA_POSTBUILD_PACKAGE_OUTPUT_SIGNATURE_{index}")
            if signature is None:
                # if signing fails with "no slots" error, we can still accept the build
                # it will get caught in signature verification
                print("Warning: No output signature")
                signature = ""
            outputs.append([value, signature])

    if not outputs:
        perror("Error: Not any POSTBUILD_PACKAGE_OUTPUT defined", 0)

    # Copy provenance file
    # refresh the narinfo to get up to date cache information
    nix_copy(cacheurl, [provenance_file], refresh=True)

    with open(provenance_file, "r", encoding="utf-8") as pb_file:
        provenance = json.load(pb_file)

    # get buildinfo from provenance file
    binfo = provenance["hydra_buildInfo"]

    # Check status of the build, we are interested only in finished builds
    if (
        binfo.get("buildStatus") != 0
        or binfo.get("finished") is not True
        or binfo.get("event") != "buildFinished"
    ):
        perror(f"Unexpected build status: {binfo.get('buildStatus')}" ", ignoring", 0)

    # Copy output paths
    for output in outputs:
        to_copy = [output[0]]
        # copy signature if it exists
        if output[1] is not None:
            to_copy.append(output[1])

        nix_copy(cacheurl, to_copy, refresh=True)

    # Copy derivation
    drv = binfo.get("drvPath")
    if drv is not None:
        nix_copy(cacheurl, [drv], derivation=True, refresh=True)

    try:
        with open(f"{bnum}.json", "r", encoding="utf-8") as json_file:
            combo = json.load(json_file)
    except FileNotFoundError:
        # If scraped json is not available, use minimal build info from env
        combo = min_info_from_env()

    translate(binfo, combo)

    package = os.getenv("HYDRA_POSTBUILD_PACKAGE")
    combo["Output package"] = package

    combo["Outputs"] = [
        {
            "output": o[0],
            "signature": o[1],
        }
        for o in outputs
    ]

    combo["Provenance"] = {
        "path": provenance_file,
        "signature": os.getenv("HYDRA_PROVENANCE_SIGNATURE"),
    }

    sd_image = None
    match = re.search(r"nix/store/[a-z0-9]{32}-(.*)\.img", outputs[0][0])
    if match is not None:
        sd_image = outputs[0][0] + "/sd-image/" + match.group(1) + ".img.zst"

    nixos_img = outputs[0][0] + "/nixos.img"

    if sd_image is not None and os.path.exists(sd_image):
        combo["Image"] = sd_image
    elif os.path.exists(nixos_img):
        combo["Image"] = nixos_img
    else:
        combo["Image"] = None

    # Write combined info to scraped build info file
    with open(f"{bnum}.json", "w", encoding="utf-8") as json_file:
        json.dump(combo, json_file, indent=2)

    # Add build to post processing list
    with open(wlist, "a", encoding="utf-8") as wlist_file:
        print(f"{bnum}:{' '.join(o[0] for o in outputs)}", file=wlist_file)


# Run main when executed from command line
if __name__ == "__main__":
    main()
