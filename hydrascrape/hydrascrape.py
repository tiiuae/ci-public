#!/usr/bin/env pipenv-shebang
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie

from urllib.error import HTTPError
import bs4
import sys
import urllib.request
import gzip
import subprocess
import os


def convert_int(str, default = 0):
    try:
        i = int(str)
    except ValueError:
        i = default
    return i


debug = convert_int(os.getenv("DEBUG"))


def help():
    print("")
    print("Usage: python3 hydrascrape.py <server> <project> <jobset> <action>")
    print("")
    print("Tries to find builds to handle for a specific jobset from a hydra server")
    print("Already handled builds will be read from <server>_<project>_<jobset>_handled_builds.txt if it exists")
    print("Successfully handled builds (action returned 0) will be added to the handled builds file")
    print("action will be run with all the build information in the environment")
    print("")
    print("For example, check environment variables starting with \"HYDRA_\":")
    print("python3 hydrascrape.py my.hydra.server myproject myjobset \"env | egrep ^HYDRA_\"")
    print("")
    sys.exit(0)


def get_page(urlctx, url):

    if debug:
        print(f"Fetching: {url}")

    req = urllib.request.Request(url, headers=urlctx["headers"])
    try:
        response = urllib.request.urlopen(req)
    except HTTPError:
        if debug:
            print("HTTP error")
        return ""

    if response.info().get('Content-Encoding') == 'gzip':
        text = gzip.decompress(response.read())
    elif response.info().get('Content-Encoding') == 'deflate':
        text = response.read()
    elif response.info().get('Content-Encoding'):
        print('Encoding type unknown')
        sys.exit(1)
    else:
        text = response.read()

    #text = text.decode('utf-8')
    return text


def get_builds(urlctx, eval):
    text = get_page(urlctx, urlctx["evalurl"] + eval)
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


def update_handled(filename, build):
    file = open(filename, "a")
    file.write(f"{build}\n")
    file.close()


def get_build_info(urlctx, bnum):
    summarykeys = {
        "Build ID": 0,
        "Status": 1,
        "System": 0,
        "Nix name": 0,
        "Nr": -1,
    }
    detailkeys = [
        "Queued at",
        "Build started",
        "Build finished",
        "Output store paths",
    ]
    text = get_page(urlctx, urlctx['buildurl'] + str(bnum))
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
                    binfo[hdr] = data.text.strip()
                except IndexError or AttributeError:
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
                except IndexError or AttributeError:
                    if debug:
                        print(f"Trouble getting {hdr}")
                    pass

    inputs = ""
    for div in soup.find_all("div",{"id": "tabs-buildinputs"}):
        for tbody in div.find_all("tbody"):
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                try:
                    input = tds[0].text.strip()
                    inputs += " " + input
                    source = tds[2].text.strip()
                    hash = tds[3].text.strip()
                    binfo[input + " hash"] = hash
                    binfo[input + " source"] = source
                except IndexError:
                    if debug:
                        print("Trouble getting build inputs")
                    pass
    binfo['Inputs'] = inputs.strip()

    return binfo


def set_env(binfo):
    env = os.environ.copy()
    for key in binfo:
        if key == "Output store paths":
            env["HYDRA_OUTPUT_STORE_HASH"] = binfo[key].removeprefix("/nix/store/").split('-', 1)[0]
        else:
            if key == "Inputs":
                env["HYDRA_INPUTS"] = binfo[key].upper()
            else:
                env["HYDRA_" + key.upper().replace(' ', '_')] = binfo[key]
    return env


def main(argv):
    if len(argv) < 4:
        help()

    server = argv[0]
    hydra = f"https://{server}/"
    project = argv[1]
    jobset = argv[2]
    filename = f"{server}_{project}_{jobset}_handled_builds.txt"
    evalsurl = f"{hydra}jobset/{project}/{jobset}"
    context = {
    "evalurl": f"{hydra}eval/",
    "buildurl": f"{hydra}build/",
    "headers": {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'Accept-Encoding': 'gzip, deflate',
               'User-Agent': 'hydrascraper.py v1.0'}
    }

    # It is assumed here that all evaluations containing builds that need processing
    # are found on the first page of evaluations listing
    text = get_page(context, evalsurl)

    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a",{"class": "row-link"})):
        # Could also use the link as-is, but just to be safe side we create new link
        builds += get_builds(context, link.text)

    # Remove duplicates
    builds = list(dict.fromkeys(builds))

    handled = []
    try:
        file = open(filename, "r")
        file_lines = file.read()
        shandled = file_lines.split("\n")
        file.close()
        for bs in shandled:
            if bs != "":
                ci = convert_int(bs, -1)
                if ci != -1:
                    handled.append(ci)
                else:
                    if debug:
                        print(f"Weird build number in handled builds file: {bs}")
        if debug:
            print(f"handled = {handled}")
    except FileNotFoundError:
        if debug:
            print(f"{filename} not found")

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
                if debug:
                    print(f"Handling {i} " + "-" * 60)
                sp = subprocess.run(argv[3], shell=True, env=env)
                if sp.returncode == 0:
                    update_handled(filename, i)
                    if debug:
                        print("Handling successful " + "-" * 55)
                else:
                    if debug:
                        print(f"{argv[2]} failed with code: {sp.returncode}")
            else:
                if debug:
                    print(f"Build {i} has failed, just marking as handled")
                update_handled(filename, i)
        else:
            if debug:
                print(f"Build {i} already handled")


if __name__ == "__main__":
    main(sys.argv[1:])
