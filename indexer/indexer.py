#!/usr/bin/env pipenv-shebang
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

import datetime
import glob
import json
import os
import sys

import jinja2
import markupsafe

domain = ".vedenemo.dev"
vulnixfiles = "vulnix*.txt"
resultfiles = "*_results/**/*.html"
sbomfiles = "sbom.*"
vulnxsfiles = "vulns.*.csv"
vulns_fixed = "vulns_fixed.*.csv"
vulns_new = "vulns_new.*.csv"
provenancefiles = "*provenance.json"
imageprefix = ""
webifyprefix = ""
debug = 0


def help(argv):
    print(
        f"""Usage: {argv[0]} IMGPFIX WEBPFIX BUILDDIR

    IMGPFIX = Image dir prefix
    WEBPFIX = Webify prefix
    BUILDDIR = build directory

makes an index file with all the build information in the build dir
Last part of the build dir needs to be the Build ID of the build being handled
Example: {argv[0]} /files/images /webify/build_reports ./1234"""
    )


# ------------------------------------------------------------------------
def convert_int(str, default=0):
    """Convert string to an int with default value if invalid string given

    @param str: String to convert
    @param default: Default value which is zero by default

    @return an integer, always
    """
    # Try converting to integer
    try:
        i = int(str)
    # If it fails, use the default value
    except (ValueError, TypeError):
        i = default
    return i


# ------------------------------------------------------------------------
# Handlers for specific build info items
# ------------------------------------------------------------------------
def server(srv, _):
    return f'<A href="https://{srv}">{srv}</A>'


# ------------------------------------------------------------------------
def project(prj, binfo):
    return f'<A href="https://{binfo["Server"]}/project/{prj}">{prj}</A>'


# ------------------------------------------------------------------------
def jobset(js, binfo):
    return (
        f'<A href="https://{binfo["Server"]}/jobset/{binfo["Project"]}/{js}">{js}</A>'
    )


# ------------------------------------------------------------------------
def job(job, binfo):
    return f'<A href="https://{binfo["Server"]}/job/{binfo["Project"]}/{binfo["Jobset"]}/{job}">{job}</A>'


# ------------------------------------------------------------------------
def build_id(bid, binfo):
    return f'<A href="https://{binfo["Server"]}/build/{bid}">{bid}</A>'


# ------------------------------------------------------------------------
def default(dat, _):
    return dat


# ------------------------------------------------------------------------
def time_stamp(tim, _):
    try:
        tim = int(tim)
    except ValueError:
        tim = 0
    dt = datetime.datetime.utcfromtimestamp(tim)
    return (
        f'<TIME datetime="{dt.strftime("%Y-%m-%dT%H:%M:%SZ")}" '
        f'data-timestamp="{tim}">{dt.strftime("%Y-%m-%d %H:%M:%S UTC")}</TIME>'
    )


# ------------------------------------------------------------------------


def postbuild_link(out, _):
    name = out.split("/", 1)[-1]
    if imageprefix is not None:
        return f'<A href="{imageprefix}/{out}">{name}</A>'
    else:
        return str(out)


# ------------------------------------------------------------------------
def homepage(hp, _):
    return f'<A href="{hp}">{hp}</A>'


# ------------------------------------------------------------------------
def inputs(inp, _):
    il = []
    for i in inp:
        il.append(
            [
                i["Name"],
                f'<A href="{i["Source"]}">{i["Source"]}</A>',
                f'<A href="{i["Source"]}/commit/{i["Hash"]}">{i["Hash"]}</A>',
            ]
        )
    return il


# ------------------------------------------------------------------------
def get_reports(fglob: str, webifypfx: str = None):
    files = glob.glob(fglob)
    if debug:
        print(files)
    res = []
    for r in files:
        link = f'<A href="{r}">{r}</A>'
        if webifypfx is not None:
            htn = None
            if r.endswith(".txt"):
                htn = r.removesuffix(".txt") + ".html"
            elif r.endswith(".csv"):
                htn = r.removesuffix(".csv") + ".html"
            if htn is not None:
                link += f' (<A href="{webifypfx}/{htn}">View as html</A>)'
        res.append(link)
    return res


# ------------------------------------------------------------------------
# Map build info items to their handlers
# ------------------------------------------------------------------------
handlers = {
    "Server": server,
    "Project": project,
    "Jobset": jobset,
    "Job": job,
    "Build ID": build_id,
    "Homepage": homepage,
    "Short description": default,
    "License": default,
    "Maintainers": default,
    "System": default,
    "Nix name": default,
    "Queued at": time_stamp,
    "Build started": time_stamp,
    "Build finished": time_stamp,
    "Post processing done at": time_stamp,
    "Derivation store path": default,
    "Output store paths": default,
    "Inputs": inputs,
    "Closure size": default,
    "Output size": default,
    "Output package": postbuild_link,
}


def main(argv: list[str]):
    """Main program"""
    global debug
    global imageprefix
    global webifyprefix
    global domain

    # Set debug if set in environment
    debug = convert_int(os.getenv("INDEXER_DEBUG"))

    # Allow override of domain
    domain = os.getenv("INDEXER_DOMAIN", domain)

    if len(argv) != 4:
        help(argv)
        return

    imageprefix = "/" + argv[1].removeprefix("/").removesuffix("/")
    webifyprefix = "/" + argv[2].removeprefix("/").removesuffix("/")

    dir = os.path.normpath(argv[3])
    # Path should end in directory which has build ID as it's name
    bnum = convert_int(os.path.basename(dir), -1)

    if bnum == -1:
        print("Could not get build number from build dir", file=sys.stderr)
        sys.exit(1)

    # Change to build dir, so we can refer files and directories relatively
    try:
        os.chdir(dir)
    except Exception:
        print(f"Could not change to directory {dir}", file=sys.stderr)
        sys.exit(1)

    # Build dir should contain <Build ID>.json where all the build info is stored
    bjson = f"{bnum}.json"
    try:
        with open(bjson, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Could not find {bjson}", file=sys.stderr)
        exit(1)

    server = data.get("Server")
    if server is None:
        print("No server indicated in json file", file=sys.stderr)
        exit(1)

    server = server.removesuffix(domain)

    imageprefix += "/" + server
    webifyprefix += "/" + server

    plink = data.get("Output package")
    if plink is None:
        print("No output package", file=sys.stderr)
        # This will disable the package link creation
        imageprefix = None

    if debug:
        print(f"imageprefix = {imageprefix}")
        print(f"webifyprefix = {webifyprefix}")

    env = jinja2.Environment(
        loader=jinja2.PackageLoader("indexer", "templates"), autoescape=False
    )  # jinja2.select_autoescape(['html']))
    template = env.get_template("index_template.html")

    binfo = {}

    # Sanitize stuff as we are not using automatic escaping
    # These comes from our system, but better safe than sorry
    for key in data:
        okey = str(markupsafe.escape(key))
        if isinstance(data[key], str):
            binfo[okey] = str(markupsafe.escape(data[key]))
        elif isinstance(data[key], list):
            ol = []
            for li in data[key]:
                if isinstance(li, str):
                    ol.append(str(markupsafe.escape(li)))
                elif isinstance(li, dict):
                    od = {}
                    for k in li:
                        od[str(markupsafe.escape(k))] = str(
                            markupsafe.escape(li[k]))
                    ol.append(od)
            binfo[okey] = ol

    # Handle build info items with their respective handlers
    result = {}
    for key in handlers:
        val = binfo.get(key, None)
        if val is not None:
            result[key] = handlers[key](val, binfo)

    # Unknown keys will be left unhandled, print them out if debug is on
    if debug:
        uk = list(set(result.keys()) - set(binfo.keys()))
        if len(uk) > 0:
            print(f"Unused keys: {uk}")

    # Find vulnix reports
    rep = get_reports(vulnixfiles, f"{webifyprefix}/{bnum}")
    if rep != []:
        result["Vulnix report"] = rep

    # Find robot framework logs and reports
    resfils = glob.glob(resultfiles)
    if debug:
        print(resfils)

    tr = []
    success = True
    for rf in resfils:
        with open(rf, "r") as file:
            while True:
                line = file.readline()
                if not line:
                    print(f"Unable to find name for report {rf}",
                          file=sys.stderr)
                    sys.exit(1)
                # It is assumed here that reports are from robot framework
                # And this is why we dig up the name like this
                if line.startswith('window.output["stats"] = [[{"'):
                    try:
                        line.index('"fail":0,"label":"All Tests"')
                    except ValueError:
                        success = False
                    line = line.split('"name":"', maxsplit=1)[1]
                    line = line.split('","', maxsplit=1)[0]
                    break
        if rf.endswith("log.html"):
            name = str(markupsafe.escape(line)) + " Log"
        else:
            name = str(markupsafe.escape(line)) + " Report"
        tr.append(f'<A href="{rf}">{name}</A>')
    if tr != []:
        result["Test results"] = tr

    # Find SBOMs
    rep = get_reports(sbomfiles)
    if rep != []:
        result["SBOM"] = rep

    # Find vulnxscan reports
    rep = get_reports(vulnxsfiles, f"{webifyprefix}/{bnum}")
    if rep != []:
        result["Vulnxscan Report"] = rep

    # Find provenance file
    rep = get_reports(provenancefiles, f"{webifyprefix}/{bnum}")
    if rep != []:
        result["SLSA Provenance"] = rep

    # Find fixed vulnerabilities
    rep = get_reports(vulns_fixed, f"{webifyprefix}/{bnum}")
    if rep != []:
        result["Fixed vulnerabilities"] = rep

    # Find new vulnerabilities
    rep = get_reports(vulns_new, f"{webifyprefix}/{bnum}")
    if rep != []:
        result["New vulnerabilities"] = rep

    # Render index.html
    with open("index.html", "w") as file:
        print(
            template.render(
                title=f"{binfo['Server']} Build {binfo['Build ID']} Results",
                result=result,
                success=success,
            ),
            file=file,
        )


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv)
