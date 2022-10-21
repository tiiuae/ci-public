#!/usr/bin/env pipenv-shebang
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie

import jinja2
import markupsafe
import sys
import json
import datetime
import os
import glob

vulnixfiles = "vulnix*.txt"
resultfiles = "*_results/**/*.html"
outputprefix = "/files/nix/store/"
debug = 0

def help():
    print("Usage: indexer.py <build dir>")
    print("")
    print("  makes an index file with all the build information in the <build dir>")
    print("  Last part (basename) of the <build dir> needs to be the Build ID of the build being handled")
    print("")


# ------------------------------------------------------------------------
# Convert string to an int with default value if invalid string given
# str = String to convert
# default = Default value which is zero by default
# Returns an integer, always
# ------------------------------------------------------------------------
def convert_int(str, default = 0):
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
    return f'<A href="https://{binfo["Server"]}/jobset/{binfo["Project"]}/{js}">{js}</A>'


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
    return f'<TIME datetime="{dt.strftime("%Y-%m-%dT%H:%M:%SZ")}" data-timestamp="{tim}">{dt.strftime("%Y-%m-%d %H:%M:%S UTC")}</TIME>'


# ------------------------------------------------------------------------
def outputs(out, _):
    ol = []
    for o in out:
        o = o.removeprefix("/nix/store/")
        ol.append(f'<A href="{outputprefix}{o}">{o}</A>')
    return ol


# ------------------------------------------------------------------------
def derivation(drv, _):
    drv = drv.removeprefix("/nix/store/")
    return drv


# ------------------------------------------------------------------------
def inputs(inp, _):
    il = []
    for i in inp:
        il.append([i["Name"], f'<A href="{i["Source"]}">{i["Source"]}</A>', f'<A href="{i["Source"]}/commit/{i["Hash"]}">{i["Hash"]}</A>'])
    return il


# ------------------------------------------------------------------------
# Map build info items to their handlers
# ------------------------------------------------------------------------
handlers =  {
    'Server': server,
    'Project': project,
    'Jobset': jobset,
    'Build ID': build_id,
    'System': default,
    'Nix name': default,
    'Finished at': time_stamp,
    'Queued at': time_stamp,
    'Build started': time_stamp,
    'Build finished': time_stamp,
    'Derivation store path': derivation,
    'Output store paths': outputs,
    'Inputs': inputs,
}

# ------------------------------------------------------------------------
# Main program
# ------------------------------------------------------------------------
def main(argv):
    global debug

    # Set debug if set in environment
    debug = convert_int(os.getenv("INDEXER_DEBUG"))

    if len(argv) != 1:
        help()
        return

    dir = os.path.normpath(argv[0])
    # Path should end in directory which has build ID as it's name
    bnum = convert_int(os.path.basename(dir), -1)

    if bnum == -1:
        print("Could not get build number from build dir", file = sys.stderr)
        sys.exit(1)

    # Change to build dir, so we can refer files and directories relatively
    try:
        os.chdir(dir)
    except:
        print(f"Could not change to directory {dir}", file = sys.stderr)
        sys.exit(1)

    # Build dir should contain <Build ID>.json where all the build info is stored
    bjson = f"{bnum}.json"
    try:
        with open(bjson, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Could not find {bjson}", file=sys.stderr)
        exit(1)

    env = jinja2.Environment(loader=jinja2.PackageLoader('indexer', 'templates'), autoescape=False) #jinja2.select_autoescape(['html']))
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
                        od[str(markupsafe.escape(k))] = str(markupsafe.escape(li[k]))
                    ol.append(od)
            binfo[okey] = ol

    # Handle build info items with their respective handlers
    result = {}
    for key in handlers:
        val = binfo.get(key, None)
        if val != None:
            result[key] = handlers[key](val, binfo)

    # Unknown keys will be left unhandled, print them out if debug is on
    if debug:
        uk = list(set(result.keys()) - set(binfo.keys()))
        if len(uk) > 0:
            print(f"Unused keys: {uk}")

    # Find vulnix reports
    vulreps = glob.glob(vulnixfiles)
    if debug:
        print(vulreps)
    vl = []
    for vr in vulreps:
        htn = vr.removesuffix(".txt") + ".html"
        vl.append(f'<A href="/webify/{bnum}/{htn}">{vr}</A>')

    result['Vulnix report'] = vl

    # Find robot framework logs and reports
    resfils = glob.glob(resultfiles)
    if debug:
        print(resfils)

    tr = []
    for rf in resfils:
        with open(rf, "r") as file:
            while True:
                line = file.readline();
                if not line:
                    print(f"Unable to find name for report {rf}", file = sys.stderr)
                    sys.exit(1)
                # It is assumed here that reports are from robot framework
                # And this is why we dig up the name like this
                if line.startswith('window.output["stats"] = [[{"'):
                    line = line.split('"name":"', maxsplit = 1)[1]
                    line = line.split('","', maxsplit = 1)[0]
                    break
        if rf.endswith("log.html"):
            name = str(markupsafe.escape(line)) + " Log"
        else:
            name = str(markupsafe.escape(line)) + " Report"
        tr.append(f'<A href="{rf}">{name}</A>')
    result['Test results'] = tr

    # Render index.html
    with open("index.html","w") as file:
            print(template.render(title=f"Build {binfo['Build ID']} Results", result=result), file=file)


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
