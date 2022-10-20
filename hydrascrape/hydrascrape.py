#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie
# ------------------------------------------------------------------------
# Script for extracting build information from a hydra server to
# facilitate further processing in e.g. Jenkins environment.
# ------------------------------------------------------------------------

import bs4
import sys
import urllib.request
import gzip
import subprocess
import os
import re
import filelock
import json
from urllib.error import HTTPError

# ------------------------------------------------------------------------
# Global debug flag
# ------------------------------------------------------------------------
debug = 0


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
# Print help and exit
# ------------------------------------------------------------------------
def help():
    print("")
    print("Usage: python3 hydrascrape.py <server> <project regexp> <jobset regexp> <handled builds file> <action> [options]")
    print("")
    print("Tries to find builds to handle for specific projects and jobsets from a hydra server")
    print("Already handled builds will be read from handled builds file if it exists")
    print("Successfully handled builds (action returned 0) will be added to the handled builds file")
    print("action will be run with all the build information in the environment")
    print("")
    print("For example, check environment variables starting with \"HYDRA_\":")
    print("python3 hydrascrape.py my.hydra.server myproject \"job.*\" myhydra_handled_builds.txt \"env | egrep ^HYDRA_\" -debug")
    print("")
    print("Available options:")
    print("  -debug  Enable debugging (You can also set DEBUG environment variable to 1)")
    print("  -json   Enable JSON output, build info will be written in JSON format to <build ID>.json before running action")
    print("  -dp     Include disabled projects in search")
    print("  -hp     Include hidden projects in search")
    print("  -dj     Include disabled jobsets in search")
    print("  -hj     Include hidden jobsets in search")
    sys.exit(0)


# ------------------------------------------------------------------------
# Fetches a page from given web site
# context = Connection context
# url = URL of the page
# Returns page data, on error returns empty page
# ------------------------------------------------------------------------
def get_page(context, url):

    if debug:
        print(f"Fetching: {url}")

    req = urllib.request.Request(url, headers = context['headers'])
    try:
        response = urllib.request.urlopen(req)
    except HTTPError as error:
        print(f"HTTP error: {error}", file = sys.stderr)
        return ""

    # Decompress if gzipped content
    if response.info().get('Content-Encoding') == 'gzip':
        text = gzip.decompress(response.read())
    elif response.info().get('Content-Encoding') == 'deflate':
        text = response.read()
    elif response.info().get('Content-Encoding'):
        print('Encoding type unknown', file = sys.stderr)
        return ""
    else:
        text = response.read()

    return text


# ------------------------------------------------------------------------
# Fetches builds for given evaluation
# context = Connection context
# Returns a list of build numbers
# ------------------------------------------------------------------------
def get_builds(context, eval):
    text = get_page(context, f"{context['hydra_url']}eval/{eval}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a",{"class": "row-link"})):
        build = convert_int(link.text.strip(),-1)
        if build != -1:
            if debug:
                print(f"Found build {build}")
            builds.append(build)

    if debug and len(builds) == 0:
        print("No builds found")

    return builds


# ------------------------------------------------------------------------
# Reads handled builds from handled builds file
# filename = Name of the handled builds file
# Returns a list of build numbers
# ------------------------------------------------------------------------
def get_handled(filename):
    handled = []
    try:
        file = open(filename, "r")
        file_lines = file.read()
        file.close()

        shandled = file_lines.split("\n")

        for bs in shandled:
            if bs != "":
                ci = convert_int(bs, -1)
                if ci != -1:
                    handled.append(ci)
                else:
                    print(f"Weird build number in handled builds file: {bs}", file=sys.stderr)

        if debug:
            print(f"handled = {handled}")

    except FileNotFoundError:
        if debug:
            print(f"{filename} not found")

    except PermissionError as pe:
        print(f"Cannot read {filename}: {pe.strerror}", file = sys.stderr)
        sys.exit(1)

    return handled


# ------------------------------------------------------------------------
# Writes handled builds into handled builds file
# filename = name of the handled builds file
# handled = list of handled build numbers
# ------------------------------------------------------------------------
def update_handled(filename, handled):
    handled.sort()
    try:
        file = open(filename, "w")
        for build in handled:
            file.write(f"{build}\n")
        file.close()

    except PermissionError as pe:
        print(f"Cannot update {filename}: {pe.strerror}", file = sys.stderr)
        sys.exit(1)

# ------------------------------------------------------------------------
# Constant data used by following get_build_info function
# ------------------------------------------------------------------------
summarykeys = {
    "Build ID": 0,
    "Status": 1,
    "System": 0,
    "Nix name": 0,
    "Finished at": 0,
    "Nr": -1,
}
detailkeys = [
    "Queued at",
    "Build started",
    "Build finished",
    "Derivation store path",
    "Output store paths",
]
# ------------------------------------------------------------------------
# Fetches information for given build number
# Returns a dictionary with information of the build
# context = Connection context
# bnum = Build ID
# ------------------------------------------------------------------------
def get_build_info(context, bnum):
    text = get_page(context, f"{context['hydra_url']}build/{bnum}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    binfo = {}

    for div in soup.find_all("div",{"id": "tabs-summary"}):
        for th in div.find_all("th"):
            hdr = th.text.strip().rstrip(':')
            val = summarykeys.get(hdr)
            if  val != None:
                if val == -1:
                    break

                try:
                    data = th.find_next_sibling().contents[val]
                    if data.name == "time":
                        binfo[hdr] = data['data-timestamp']
                    else:
                        binfo[hdr] = data.text.strip()
                except (IndexError, AttributeError):
                    if debug:
                        print(f"Trouble getting {hdr}")
                    pass

    for div in soup.find_all("div",{"id": "tabs-details"}):
        for th in div.find_all("th"):
            hdr = th.text.strip().rstrip(':')
            if hdr in detailkeys:
                try:
                    data = th.find_next_sibling().contents[0]
                    if data.name == "time":
                        binfo[hdr] = data['data-timestamp']
                    else:
                        binfo[hdr] = data.text.strip()
                except (IndexError, AttributeError):
                    if debug:
                        print(f"Trouble getting {hdr}")
                    pass

    inputs = []
    for div in soup.find_all("div",{"id": "tabs-buildinputs"}):
        for tbody in div.find_all("tbody"):
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                try:
                    input = tds[0].text.strip()
                    source = tds[2].text.strip()
                    hash = tds[3].text.strip()
                    inputs.append({"Name": input,
                               "Hash": hash,
                               "Source": source})
                except IndexError:
                    if debug:
                        print("Trouble getting build inputs")
                    pass
    binfo['Inputs'] = inputs
    binfo['Output store paths'] = binfo['Output store paths'].split(',')

    return binfo


# ------------------------------------------------------------------------
# Sets environment variables based on given dictionary
# binfo = Dictionary containing build information
# Returns environment dictionary
# ------------------------------------------------------------------------
def set_env(binfo):
    env = os.environ.copy()

    for key in binfo:
        if key == "Output store paths":
            # Set the plain hash of the first output separately
            env["HYDRA_OUTPUT_STORE_HASH"] = binfo[key][0].removeprefix("/nix/store/").split('-', 1)[0]
            env["HYDRA_OUTPUT_STORE_PATHS"] = ','.join(binfo[key])
            continue
        if key == "Derivation store path":
            # Set the plain hash of the derivation separately
            env["HYDRA_DERIVATION_STORE_HASH"] = binfo[key].removeprefix("/nix/store/").split('-', 1)[0]
        if key == "Inputs":
            env["HYDRA_INPUTS"] = ""
            for i in binfo[key]:
                env["HYDRA_INPUTS"] += f"{i['Name'].upper()} "
                env[f"HYDRA_{i['Name'].upper()}_HASH"] = i['Hash']
                env[f"HYDRA_{i['Name'].upper()}_SOURCE"] = i['Source']
            env["HYDRA_INPUTS"] = env["HYDRA_INPUTS"].strip()
            continue
        env["HYDRA_" + key.upper().replace(' ', '_')] = binfo[key]

    return env


# ------------------------------------------------------------------------
# Saves given given build information dictionary in json format
# binfo = Dictionary containing build information
# ------------------------------------------------------------------------
def save_json(binfo):
    filename = f"{binfo['Build ID']}.json"
    if debug:
        print(f"Writing json info into {filename}")

    json_obj = json.dumps(binfo, indent=2)

    try:
        with open(filename, "w") as outf:
            outf.write(json_obj)

    except PermissionError as pe:
        print(f"Could not write {pe.filename}: {pe.strerror}", file = sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------------
# Gets projects from a hydra site
# context = Connection context
# ------------------------------------------------------------------------
def get_projects(context):
    text = get_page(context, context['hydra_url'])
    soup = bs4.BeautifulSoup(text, features="html.parser")

    projects = soup.find_all("tr", {"class": "project"})
    hiddens = soup.find_all("span", {"class": "hidden-project"})
    disableds = soup.find_all("span", {"class": "disabled-project"})

    plist = []
    for p in projects:
        plist.append(p.find("a", {"class": "row-link"})["href"].split("/")[-1])

    hlist = []
    for h in hiddens:
        hlist.append(h.find("a", {"class": "row-link"})["href"].split("/")[-1])

    dlist = []
    for d in disableds:
        dlist.append(d.find("a", {"class": "row-link"})["href"].split("/")[-1])

    if context['hid_proj'] == False:
        for h in hlist:
            if h in plist:
                plist.remove(h)

    if context['dis_proj'] == False:
        for d in dlist:
            if d in plist:
                plist.remove(d)

    if debug:
        print("Found projects: ", plist)

    return plist


# ------------------------------------------------------------------------
# Gets jobsets for a given hydra project
# context = Connection context
# ------------------------------------------------------------------------
def get_jobsets(context, project):
    text = get_page(context, f"{context['hydra_url']}project/{project}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    jobsets = soup.find_all("tr", {"class": "jobset"})
    hiddens = soup.find_all("span", {"class": "hidden-jobset"})
    disableds = soup.find_all("span", {"class": "disabled-jobset"})

    jlist = []
    for j in jobsets:
        jlist.append(j.find("a", {"class": "row-link"})["href"].split("/")[-1])

    hlist = []
    for h in hiddens:
        hlist.append(d.find("a", {"class": "row-link"})["href"].split("/")[-1])

    dlist = []
    for d in disableds:
        dlist.append(d.find("a", {"class": "row-link"})["href"].split("/")[-1])

    if context['hid_jobset'] == False:
        for h in hlist:
            if h in jlist:
                jlist.remove(h)

    if context['dis_jobset'] == False:
        for d in dlist:
            if d in jlist:
                jlist.remove(d)

    if debug:
        print("Found jobsets: ", jlist)

    return jlist

# ------------------------------------------------------------------------
# Handles a given jobset of given project
# context = Connection context
# project = Project name
# jobset = Jobset name
# handled = list of handled builds
# ------------------------------------------------------------------------
def handle_jobset(context, project, jobset, handled):
    # It is assumed here that all evaluations containing builds that need processing
    # are found on the first page of evaluations listing
    text = get_page(context, f"{context['hydra_url']}jobset/{project}/{jobset}")

    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a",{"class": "row-link"})):
        # Could also use the link as-is, but just to be safe side we create new link
        builds += get_builds(context, link.text)

    # Remove duplicates
    builds = list(dict.fromkeys(builds))

    new_handled = []

    for i in builds:
        if i not in handled:
            binfo = get_build_info(context, i)
            buildid = convert_int(binfo.get('Build ID'), -1)

            if buildid != i:
                if debug:
                    print(f"Build ID mismatch: build id on page = {buildid}, build id requested = {i}, skipping")
                continue

            status = binfo.get('Status','Unknown')

            if status == "Scheduled to be built" or status == "Build in progress":
                if debug:
                    print(f"Build {i} not finished yet, skipping")
                continue

            if status == "Success":
                binfo['Server'] = context['server']
                binfo['Project'] = project
                binfo['Jobset'] = jobset
                del binfo['Status']
                env = set_env(binfo)
                if context['json_en']:
                    save_json(binfo)
                if debug:
                    print(f"Handling {i} " + "-" * 60)

                # Run the user specified action with build info in environment
                sp = subprocess.run(context['action'], shell=True, env=env)

                if sp.returncode == 0:
                    new_handled.append(i)
                    if debug:
                        print("Handling successful " + "-" * 55)
                else:
                    if debug:
                        print(f"Action failed with code: {sp.returncode}")
            else:
                if debug:
                    print(f"Build {i} has failed, just marking as handled")
                new_handled.append(i)
        else:
            if debug:
                print(f"Build {i} already handled")

    return new_handled


# ------------------------------------------------------------------------
# locked main program, called only if lock was aqcuired successfully
# context = Connection context
# ------------------------------------------------------------------------
def main_locked(context):
    context['hydra_url'] = f"https://{context['server']}/"
    context['headers'] = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                          'Accept-Encoding': 'gzip, deflate',
                          'User-Agent': 'hydrascraper.py v1.0'}

    handled = get_handled(context['handled_file'])

    projects = get_projects(context)
    projects = list(filter(context['re_p'].match, projects))
    if debug:
        print("Selected projects: ", projects)

    jobsets = {}
    for p in projects:
        jobsets[p] = get_jobsets(context, p)

    for p in projects:
        jobsets[p] = list(filter(context['re_js'].match, jobsets[p]))
        if debug:
            print(f"{p} selected jobsets: {jobsets[p]}")

    for p in projects:
        project = p
        for j in jobsets[p]:
            jobset = j
            handled += handle_jobset(context, project, jobset, handled)

    update_handled(context['handled_file'], handled)


# ------------------------------------------------------------------------
# Enable JSON output in context
# context = Connection context
# ------------------------------------------------------------------------
def json_e(context):
    context['json_en'] = True
    if debug:
        print("JSON enabled")


# ------------------------------------------------------------------------
# Set global debug flag
# ------------------------------------------------------------------------
def debug_e(_):
    global debug
    debug = 1
    print("Debug enabled")


# ------------------------------------------------------------------------
# Set hidden projects flag in context
# context = Connection context
# ------------------------------------------------------------------------
def hp_e(context):
    context['hid_proj'] = True
    if debug:
        print("Including hidden projects")


# ------------------------------------------------------------------------
# Set disabled projects flag in context
# context = Connection context
# ------------------------------------------------------------------------
def dp_e(context):
    context['dis_proj'] = True
    if debug:
        print("Including disabled projects")


# ------------------------------------------------------------------------
# Set hidden jobsets flag in context
# context = Connection context
# ------------------------------------------------------------------------
def hj_e(context):
    context['hid_jobset'] = True
    if debug:
        print("Including hidden jobsets")


# ------------------------------------------------------------------------
# Set disabled jobsets flag in context
# context = Connection context
# ------------------------------------------------------------------------
def dj_e(context):
    context['dis_jobset'] = True
    if debug:
        print("Including disabled jobsets")

# ------------------------------------------------------------------------
# Main function
# argv = Command line parameters
# ------------------------------------------------------------------------
def main(argv):
    global debug
    # Set debug if set in environment
    debug = convert_int(os.getenv("DEBUG"))

    # Map options to functions setting the flags
    argfu = {"-json": json_e,
             "-debug": debug_e,
             "-hp": hp_e,
             "-dp": dp_e,
             "-hj": hj_e,
             "-dj": dj_e,
    }

    # Default settings in context
    context = {'json_en': False,
               'dis_proj': False,
               'hid_proj': False,
               'dis_jobset': False,
               'hid_jobset': False}

    # Help user, too few arguments given
    if len(argv) < 5:
        help()

    context['server'] = argv[0]

    r = []
    for i in [0,1]:
        try:
            # Create regular expression objects of project and jobset strings
            r.append(re.compile(argv[i + 1]))
        except re.error as e:
            if e.pos != None:
                print(argv[i + 1], file = sys.stderr)
                print(" " * e.pos + "^", file = sys.stderr)
            print(f"Regular expression error: {e.msg}", file = sys.stderr)
            sys.exit(1)

    context['re_p'] = r[0]
    context['re_js'] = r[1]
    context['handled_file'] = argv[3]
    context['action'] = argv[4]

    if len(argv) > 5:
        # Process options
        for i in range(5, len(argv)):
            f = argfu.get(argv[i], None)
            if f != None:
                f(context)
            else:
                print(f"Invalid argument: {argv[i]}", file=sys.stderr)
                sys.exit(1)

    lock = filelock.FileLock(f"{argv[3]}.lock")
    try:
        lock.acquire(timeout=0)
        main_locked(context)

    except filelock.Timeout as to:
        if debug:
            print(f"Unable to get lock {to.lock_file}")
            print("If no other hydrascrapers are running, check permissions and/or delete the lock file")

    except PermissionError as pe:
        print(f"Could not aquire {argv[3]}.lock: {pe.strerror}", file = sys.stderr)

    finally:
        lock.release()


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
