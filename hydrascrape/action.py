#!/usr/bin/env pipenv-shebang
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2023 Unikie
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# ------------------------------------------------------------------------
# Action script for hydra scraper
# ------------------------------------------------------------------------
import sys
import os
import json
import subprocess


# ------------------------------------------------------------------------
# Prints an error message and exits
# txt = Error message
# code = optional exit code
# ------------------------------------------------------------------------
def perror(txt, code=1):
    print(txt, file=sys.stderr)
    sys.exit(code)


# ------------------------------------------------------------------------
# Copies stuff from cache
# ------------------------------------------------------------------------
def nix_copy(cacheurl: str, paths: list[str], derivation: bool = False):
    if len(paths) < 1:
        return

    nixcopy = ['nix', 'copy', '--from', cacheurl]
    if derivation:
        nixcopy.insert(2, '--derivation')

    nixcopy.extend(paths)

    result = subprocess.run(nixcopy, stdout=subprocess.PIPE)
    if result.returncode != 0:
        perror(result.stderr, result.returncode)


# ------------------------------------------------------------------------
# Convert hydra json style outputs to plain list of paths
# iout = outputs list in hydra json style
# returns = list of paths (maybe empty)
# ------------------------------------------------------------------------
def get_outputs(iout: list[dict] | None) -> list:
    oout = []
    if iout != None:
        for output in iout:
            outp = output.get('path')
            if outp != None:
                oout.append(outp)
    return oout


# ------------------------------------------------------------------------
# Translate table for json items, used by translate function
# ------------------------------------------------------------------------
transtable = {
    "build": "Build ID",
    "system": "System",
    "nixName": "Nix name",
    "timestamp": "Queued at",
    "startTime": "Build started",
    "stopTime": "Build finished",
    "drvPath": "Derivation store path",
    "job": "Job",
    "imageLink": "Postbuild link",
    "project": "Project",
    "jobset": "Jobset",
    "homepage": "Homepage",
    "description": "Short description",
    "license": "License",
}

# ------------------------------------------------------------------------
# Translate hydra post build json to more readable (scraped-like) json
# ibinfo: dictionary containing hydra post build json
# obinfo: dictionary containing scraped values
#   values overwritten or appended, may be empty
# ------------------------------------------------------------------------
def translate(ibinfo: dict, obinfo: dict):
    for k in transtable:
        nk = transtable[k]
        val = ibinfo.get(k)
        if val != None:
            # Convert all to strings
            val = str(val)
            oval = obinfo.get(nk)
            # Check and warn if there's contradicting info
            if oval != None and oval != val:
                print( "Warning! differing build information:", file=sys.stderr)
                print(f"  {k} = {val}", file=sys.stderr)
                print(f"  {nk} = {oval}", file=sys.stderr)
            # Trust the nix-store json file rather than scraped stuff
            obinfo[nk] = val

    # Handle outputs separately
    ooutputs = get_outputs(ibinfo.get('outputs'))

    # Check outputs also
    obio = obinfo.get('Output store paths')
    if obio != None and obio != ooutputs:
        print( "Warning! differing build information:", file=sys.stderr)
        print(f"  outputs = {ooutputs}", file=sys.stderr)
        print(f"  Output store paths = {obio}", file=sys.stderr)

    obinfo['Output store paths'] = ooutputs


# ------------------------------------------------------------------------
# Get minimal build info from environment variables
# (Rest should be in post build json file)
# return = dictionary of build info
# ------------------------------------------------------------------------
def min_info_from_env() -> dict:
    envl = ["Server", "Postbuild info", "Maintainers", "Closure size", "Output size" ]
    res = {}

    for k in envl:
        ev = os.getenv(f"HYDRA_{k.upper().replace(' ','_')}")
        if ev != None:
            res[k] = ev
    return res


# ------------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------------
def main(argv: list[str]):
    cacheurl = "https://cache.vedenemo.dev"
    wlist = "wlist.txt"

    # Allow cache url override
    cacheurl = os.getenv("ACTION_CACHEURL", cacheurl)

    # Allow wlist file name override
    wlist = os.getenv("ACTION_WLISTFILE", wlist)

    bnum = os.getenv("HYDRA_BUILD_ID")
    if bnum == None:
        perror("Error: HYDRA_BUILD_ID not defined")

    print(f"Hydra Build ID: {bnum}")

    jsonf = os.getenv("HYDRA_POSTBUILD_INFO")
    if jsonf == None:
        # Return zero so this build will be marked as handled
        perror("Warning: HYDRA_POSTBUILD_INFO not defined, ignoring old build", 0)

    # Copy build info json file
    nix_copy(cacheurl, [jsonf])

    with open(jsonf,"r") as fh:
        binfo = json.load(fh)

    # Check status of the build, we are interested only in finished builds
    if binfo.get('buildStatus') != 0 or binfo.get('finished') != True or binfo.get('event') != "buildFinished":
        perror(f"Unexpected build status: {binfo.get('buildStatus')}, ignoring", 0)

    # Find output paths
    outps = get_outputs(binfo.get('outputs'))

    if len(outps) == 0:
        perror("Outputs not found, ignoring", 0)

    # Copy output paths
    nix_copy(cacheurl, outps)

    # Copy derivation
    drv = binfo.get('drvPath')
    if drv != None:
        nix_copy(cacheurl, [drv], derivation=True)

    # Copy image link
    link = binfo.get('imageLink')
    if link != None:
        nix_copy(cacheurl, [link])

    try:
        with open(f"{bnum}.json", "r") as jf:
            combo = json.load(jf)
    except FileNotFoundError:
        # If scraped json file is not available, use minimal build info from env
        combo = min_info_from_env()

    translate(binfo, combo)

    # Write combined info to scraped build info file
    with open(f"{bnum}.json", "w") as jf:
        json.dump(combo, jf, indent=2)

    # Add build to post processing list
    with open(wlist, "a") as wf:
        print(f"{bnum}:{' '.join(outps)}", file=wf)

# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv)
