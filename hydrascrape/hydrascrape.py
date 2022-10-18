#!/usr/bin/env pipenv-shebang
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie

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

debug = False
jsonen = False
hid_proj = False
dis_proj = False
hid_jobset = False
dis_jobset = False


def convert_int(str, default = 0):
    try:
        i = int(str)
    except (ValueError, TypeError):
        i = default
    return i


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


def get_page(urlctx, url):

    if debug:
        print(f"Fetching: {url}")

    req = urllib.request.Request(url, headers=urlctx["headers"])
    try:
        response = urllib.request.urlopen(req)
    except HTTPError as error:
        print(f"HTTP error: {error}", file = sys.stderr)
        return ""

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


def get_builds(urlctx, eval):
    hydra = urlctx['hydraurl']
    text = get_page(urlctx, f"{hydra}eval/{eval}")
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


def get_build_info(urlctx, bnum):
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
    hydra = urlctx['hydraurl']
    text = get_page(urlctx, f"{hydra}build/{bnum}")
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


def set_env(binfo):
    env = os.environ.copy()

    for key in binfo:
        if key == "Output store paths":
            env["HYDRA_OUTPUT_STORE_HASH"] = binfo[key][0].removeprefix("/nix/store/").split('-', 1)[0]
            env["HYDRA_OUTPUT_STORE_PATHS"] = ','.join(binfo[key])
            continue
        if key == "Derivation store path":
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


def save_json(binfo):
    if jsonen:
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


def get_projects(urlctx, hidden=False, disabled=False):
    text = get_page(urlctx, urlctx['hydraurl'])
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

    if hidden == False:
        for h in hlist:
            if h in plist:
                plist.remove(h)

    if disabled == False:
        for d in dlist:
            if d in plist:
                plist.remove(d)

    if debug:
        print("Found projects: ", plist)

    return plist


def get_jobsets(urlctx, project, hidden=False, disabled=False):
    hydra = urlctx['hydraurl']
    text = get_page(urlctx, f"{hydra}project/{project}")
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

    if hidden == False:
        for h in hlist:
            if h in jlist:
                jlist.remove(h)

    if disabled == False:
        for d in dlist:
            if d in jlist:
                jlist.remove(d)

    if debug:
        print("Found jobsets: ", jlist)

    return jlist


def handle_jobset(context, project, jobset, handled):
    server = context['server']
    hydra = context['hydraurl']
    # It is assumed here that all evaluations containing builds that need processing
    # are found on the first page of evaluations listing
    text = get_page(context, f"{hydra}jobset/{project}/{jobset}")

    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a",{"class": "row-link"})):
        # Could also use the link as-is, but just to be safe side we create new link
        builds += get_builds(context, link.text)

    # Remove duplicates
    builds = list(dict.fromkeys(builds))

    newbs = []

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
                binfo['Server'] = server
                binfo['Project'] = project
                binfo['Jobset'] = jobset
                del binfo['Status']
                env = set_env(binfo)
                save_json(binfo)
                if debug:
                    print(f"Handling {i} " + "-" * 60)
                sp = subprocess.run(context['action'], shell=True, env=env)
                if sp.returncode == 0:
                    newbs.append(i)
                    if debug:
                        print("Handling successful " + "-" * 55)
                else:
                    if debug:
                        print(f"Action failed with code: {sp.returncode}")
            else:
                if debug:
                    print(f"Build {i} has failed, just marking as handled")
                newbs.append(i)
        else:
            if debug:
                print(f"Build {i} already handled")

    return newbs


def main_locked(argv):
    server = argv[0]
    filename = argv[3]
    context = {
    "server": server,
    "hydraurl": f"https://{server}/",
    "headers": {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'hydrascraper.py v1.0'},
    "action": argv[4],
    }

    r = []
    for i in [0,1]:
        try:
            r.append(re.compile(argv[i + 1]))
        except re.error as e:
            if e.pos != None:
                print(argv[i + 1], file = sys.stderr)
                print(" " * e.pos + "^", file = sys.stderr)
            print(f"Regular expression error: {e.msg}", file = sys.stderr)
            sys.exit(1)

    handled = get_handled(filename)

    projects = get_projects(context, hidden=hid_proj, disabled=dis_proj)
    projects = list(filter(r[0].match, projects))
    if debug:
        print("Selected projects: ", projects)

    jobsets = {}
    for p in projects:
        jobsets[p] = get_jobsets(context, p, hidden=hid_jobset, disabled=dis_jobset)

    for p in projects:
        jobsets[p] = list(filter(r[1].match, jobsets[p]))
        if debug:
            print(f"{p} selected jobsets: {jobsets[p]}")

    for p in projects:
        project = p
        for j in jobsets[p]:
            jobset = j
            handled += handle_jobset(context, project, jobset, handled)

    update_handled(filename, handled)


def json_e():
    global jsonen
    jsonen = True
    if debug:
        print("JSON enabled")


def debug_e():
    global debug
    debug = 1
    print("Debug enabled")


def hp_e():
    global hid_proj
    hid_proj = True
    if debug:
        print("Including hidden projects")


def dp_e():
    global dis_proj
    dis_proj = True
    if debug:
        print("Including disabled projects")


def hj_e():
    global hid_jobset
    hid_jobset = True
    if debug:
        print("Including hidden jobsets")


def dj_e():
    global dis_jobset
    dis_jobset = True
    if debug:
        print("Including disabled jobsets")


def main(argv):
    global debug
    debug = convert_int(os.getenv("DEBUG"))

    argfu = {"-json": json_e,
             "-debug": debug_e,
             "-hp": hp_e,
             "-dp": dp_e,
             "-hj": hj_e,
             "-dj": dj_e,
    }

    if len(argv) < 5:
        help()

    if len(argv) > 5:
        for i in range(5, len(argv)):
            f = argfu.get(argv[i], None)
            if f != None:
                f()
            else:
                print(f"Invalid argument: {argv[i]}", file=sys.stderr)
                sys.exit(1)

    lock = filelock.FileLock(f"{argv[3]}.lock")
    try:
        lock.acquire(timeout=0)
        main_locked(argv)

    except filelock.Timeout as to:
        if debug:
            print(f"Unable to get lock {to.lock_file}")
            print("If no other hydrascrapers are running, check permissions and/or delete the lock file")

    except PermissionError as pe:
        print(f"Could not aquire {argv[3]}.lock: {pe.strerror}", file = sys.stderr)

    finally:
        lock.release()


if __name__ == "__main__":
    main(sys.argv[1:])
