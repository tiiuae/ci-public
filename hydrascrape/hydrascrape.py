#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
"""
Script for extracting build information from a hydra server to
facilitate further processing in e.g. Jenkins environment.
"""

import gzip
import json
import os
import re
import subprocess
import sys
import urllib.request
from urllib.error import HTTPError

import bs4
import filelock

# Global debug flag
DEBUG = 0


def convert_int(input_str, default=0):
    """Convert string to an int with default value if invalid string given

    @param str: String to convert
    @param default: Default value which is zero by default

    @return: an integer, always
    """
    # Try converting to integer
    try:
        i = int(input_str)
    # If it fails, use the default value
    except (ValueError, TypeError):
        i = default
    return i


def send_help():
    """Print help and exit"""
    # pylint: disable=line-too-long

    print("""
Usage: python3 hydrascrape.py <server> <project regexp> <jobset regexp> <handled builds file> <action> [options]

Tries to find builds to handle for specific projects and jobsets from a hydra server
Already handled builds will be read from handled builds file if it exists
Successfully handled builds (action returned 0) will be added to the handled builds file
action will be run with all the build information in the environment

For example, check environment variables starting with \"HYDRA_\":
python3 hydrascrape.py my.hydra.server myproject 'job.*' '.*' myhydra_handled_builds.txt 'env | egrep ^HYDRA_' -debug

Available options:
  -debug  Enable debugging (You can also set DEBUG environment variable to 1)
  -json   Enable JSON output, build info will be written in JSON format to <build ID>.json before running action
  -dp     Include disabled projects in search
  -hp     Include hidden projects in search
  -dj     Include disabled jobsets in search
  -hj     Include hidden jobsets in search
    """)
    sys.exit(0)


def get_page(context, url):
    """Fetches a page from given web site

    @param context: Connection context
    @param url: URL of the page

    @return: page data, on error returns empty page
    """
    if DEBUG:
        print(f"Fetching: {url}")

    req = urllib.request.Request(url, headers=context['headers'])
    try:
        response = urllib.request.urlopen(req)
    except HTTPError as error:
        print(f"HTTP error: {error}", file=sys.stderr)
        return ""

    # Decompress if gzipped content
    if response.info().get('Content-Encoding') == 'gzip':
        text = gzip.decompress(response.read())
    elif response.info().get('Content-Encoding') == 'deflate':
        text = response.read()
    elif response.info().get('Content-Encoding'):
        print('Encoding type unknown', file=sys.stderr)
        return ""
    else:
        text = response.read()

    return text


def get_builds(context, evaluation):
    """Fetches builds for given evaluation

    @param context: Connection context

    @return: a list of build numbers
    """
    text = get_page(context, f"{context['hydra_url']}eval/{evaluation}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a", {"class": "row-link"})):
        build = convert_int(link.text.strip(), -1)
        if build != -1:
            if DEBUG:
                print(f"Found build {build}")
            builds.append(build)

    if DEBUG and len(builds) == 0:
        print("No builds found")

    return builds


def get_handled(filename):
    """Reads handled builds from handled builds file

    @param filename: Name of the handled builds file

    @return: a list of build numbers
    """
    handled = []
    try:
        with open(filename, "r", encoding="utf-8") as handled_file:
            file_lines = handled_file.read()
            build_ids = file_lines.split("\n")

        for bid in build_ids:
            if bid != "":
                as_int = convert_int(bid, -1)
                if as_int != -1:
                    handled.append(as_int)
                else:
                    print(f"Weird build number in handled builds file: {bid}",
                          file=sys.stderr)

        if DEBUG:
            print(f"handled = {handled}")

    except FileNotFoundError:
        if DEBUG:
            print(f"{filename} not found")

    except PermissionError as perm_error:
        print(f"Cannot read {filename}: {perm_error.strerror}",
              file=sys.stderr)
        sys.exit(1)

    return handled


def update_handled(filename, handled):
    """Writes handled builds into handled builds file

    @param filename: name of the handled builds file
    @param handled: list of handled build numbers
    """
    handled.sort()
    try:
        with open(filename, "w", encoding="utf-8") as handled_file:
            for build in handled:
                handled_file.write(f"{build}\n")

    except PermissionError as perm_error:
        print(
            f"Cannot update {filename}: {perm_error.strerror}", file=sys.stderr)
        sys.exit(1)


def get_postbuild_info(context: dict, log_hash: str, binfo: dict):
    """Get info provided by the Hydra postbuild script"""
    # Get run command log by hash
    text = get_page(context, f"{context['hydra_url']}runcommandlog/{log_hash}")
    # Convert bytes to string
    text = text.decode("utf-8")
    # Create regex pattern that matches simple variable="value" assignments
    pat = re.compile('^.*=".*"$')

    # Handle line by line
    for line in text.split('\n'):
        # Throw away extra spaces
        line = line.strip()
        # If pattern matches store the value in binfo
        if pat.match(line):
            varname = line.split("=")[0].lower().capitalize().replace('_', ' ')
            value = line.split('"')[1]
            binfo[varname] = value


# Constant data used by following get_build_info function
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
    "Short description",
    "License",
    "Homepage",
    "Maintainers",
    "Derivation store path",
    "Output store paths",
    "Closure size",
    "Output size",
]


def get_build_info(context, bnum):
    """Fetches information for given build number

    @param context: Connection context
    @param bnum: Build ID

    @return a dictionary with information of the build
    """
    text = get_page(context, f"{context['hydra_url']}build/{bnum}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    binfo = {}

    for div in soup.find_all("div", {"id": "tabs-summary"}):
        for header in div.find_all("th"):
            hdr = header.text.strip().rstrip(':')
            val = summarykeys.get(hdr)
            if val is not None:
                if val == -1:
                    break

                try:
                    data = header.find_next_sibling().contents[val]
                    if data.name == "time":
                        binfo[hdr] = data['data-timestamp']
                    else:
                        binfo[hdr] = data.text.strip()
                except (IndexError, AttributeError):
                    if DEBUG:
                        print(f"Trouble getting {hdr}")

    for div in soup.find_all("div", {"id": "tabs-details"}):
        for header in div.find_all("th"):
            hdr = header.text.strip().rstrip(':').replace('(', '').replace(')', '')
            if hdr in detailkeys:
                try:
                    data = header.find_next_sibling().contents[0]
                    if data.name == "time":
                        binfo[hdr] = data['data-timestamp']
                    else:
                        val = data.text.split('\n')[0].strip()
                        if val != "not given":
                            binfo[hdr] = val

                except (IndexError, AttributeError):
                    if DEBUG:
                        print(f"Trouble getting {hdr}")

    inputs = []
    for div in soup.find_all("div", {"id": "tabs-buildinputs"}):
        for tbody in div.find_all("tbody"):
            for row in tbody.find_all("tr"):
                tds = row.find_all("td")
                try:
                    input_name = tds[0].text.strip()
                    input_source = tds[2].text.strip()
                    input_hash = tds[3].text.strip()
                    inputs.append({"Name": input_name,
                                   "Hash": input_hash,
                                   "Source": input_source})
                except IndexError:
                    if DEBUG:
                        print("Trouble getting build inputs")
    if len(inputs) > 0:
        binfo['Inputs'] = inputs
    binfo['Output store paths'] = binfo['Output store paths'].split(' ')
    binfo['Job'] = soup.find(
        "div", {"class": "page-header"}).text.split(':')[-1].strip()

    # Find run command log hash entries for build
    loghash = None
    for link in soup.find_all("a", {"class": "btn btn-secondary btn-sm"}):
        href = link.get('href')
        if (
            href is not None
            and href.find("/runcommandlog/") != -1
            and href.endswith("/raw")
        ):
            loghash = href.split("/")[-2]
            # First one should be latest, no need to dig deeper
            break

    # If found, then process log for post build data
    if loghash is not None:
        get_postbuild_info(context, loghash, binfo)

    return binfo


def set_env(binfo):
    """Sets environment variables based on given dictionary

    @param binfo: Dictionary containing build information

    @return: environment dictionary
    """
    env = os.environ.copy()

    for key in binfo:
        if key == "Output store paths":
            # Set the plain hash of the first output separately
            env["HYDRA_OUTPUT_STORE_HASH"] = binfo[key][0].removeprefix(
                "/nix/store/").split('-', 1)[0]
            env["HYDRA_OUTPUT_STORE_PATHS"] = ' '.join(binfo[key])
            continue
        if key == "Derivation store path":
            # Set the plain hash of the derivation separately
            env["HYDRA_DERIVATION_STORE_HASH"] = binfo[key].removeprefix(
                "/nix/store/").split('-', 1)[0]
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
    """Saves given given build information dictionary in json format

    @param binfo: Dictionary containing build information
    """
    filename = f"{binfo['Build ID']}.json"
    if DEBUG:
        print(f"Writing json info into {filename}")

    json_obj = json.dumps(binfo, indent=2)

    try:
        with open(filename, "w", encoding="utf-8") as outf:
            outf.write(json_obj)

    except PermissionError as perm_error:
        print(f"Could not write {perm_error.filename}: {perm_error.strerror}",
              file=sys.stderr)
        sys.exit(1)


def get_projects(context):
    """Gets projects from a hydra site
    @param context: Connection context
    """
    text = get_page(context, context['hydra_url'])
    soup = bs4.BeautifulSoup(text, features="html.parser")

    projects = soup.find_all("tr", {"class": "project"})
    hiddens = soup.find_all("span", {"class": "hidden-project"})
    disableds = soup.find_all("span", {"class": "disabled-project"})

    plist = []
    for proj in projects:
        plist.append(
            proj.find("a", {"class": "row-link"})["href"].split("/")[-1])

    hlist = []
    for proj in hiddens:
        hlist.append(
            proj.find("a", {"class": "row-link"})["href"].split("/")[-1])

    dlist = []
    for proj in disableds:
        dlist.append(
            proj.find("a", {"class": "row-link"})["href"].split("/")[-1])

    if context['hid_proj'] is False:
        for proj in hlist:
            if proj in plist:
                plist.remove(proj)

    if context['dis_proj'] is False:
        for proj in dlist:
            if proj in plist:
                plist.remove(proj)

    if DEBUG:
        print("Found projects: ", plist)

    return plist


def get_jobsets(context, project):
    """Gets jobsets for a given hydra project

    @param context: Connection context
    """
    text = get_page(context, f"{context['hydra_url']}project/{project}")
    soup = bs4.BeautifulSoup(text, features="html.parser")

    jobsets = soup.find_all("tr", {"class": "jobset"})
    hiddens = soup.find_all("span", {"class": "hidden-jobset"})
    disableds = soup.find_all("span", {"class": "disabled-jobset"})

    jlist = []
    for jobset in jobsets:
        jlist.append(jobset.find(
            "a", {"class": "row-link"})["href"].split("/")[-1])

    hlist = []
    for jobset in hiddens:
        hlist.append(jobset.find(
            "a", {"class": "row-link"})["href"].split("/")[-1])

    dlist = []
    for jobset in disableds:
        dlist.append(jobset.find(
            "a", {"class": "row-link"})["href"].split("/")[-1])

    if context['hid_jobset'] is False:
        for jobset in hlist:
            if jobset in jlist:
                jlist.remove(jobset)

    if context['dis_jobset'] is False:
        for jobset in dlist:
            if jobset in jlist:
                jlist.remove(jobset)

    if DEBUG:
        print("Found jobsets: ", jlist)

    return jlist


def handle_jobset(context, project, jobset, handled):
    """Handles a given jobset of given project

    @param context: Connection context
    @param project: Project name
    @param jobset: Jobset name
    @param handled: list of handled builds
    """
    # It is assumed here that all evaluations containing builds that need processing
    # are found on the first page of evaluations listing
    text = get_page(
        context, f"{context['hydra_url']}jobset/{project}/{jobset}")

    soup = bs4.BeautifulSoup(text, features="html.parser")

    builds = []
    for link in reversed(soup.find_all("a", {"class": "row-link"})):
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
                if DEBUG:
                    print(f"Build ID mismatch: build id on page = {buildid}, "
                          f"build id requested = {i}, skipping")
                continue

            status = binfo.get('Status', 'Unknown')

            if status in ("Scheduled to be built", "Build in progress"):
                if DEBUG:
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
                if DEBUG:
                    print(f"Handling {i} " + "-" * 60)

                # Run the user specified action with build info in environment
                result = subprocess.run(context['action'], shell=True,
                                        env=env, check=False)

                if result.returncode == 0:
                    new_handled.append(i)
                    if DEBUG:
                        print("Handling successful " + "-" * 55)
                else:
                    if DEBUG:
                        print(f"Action failed with code: {result.returncode}")
            else:
                if DEBUG:
                    print(f"Build {i} has failed, just marking as handled")
                new_handled.append(i)
        else:
            if DEBUG:
                print(f"Build {i} already handled")

    return new_handled


def main_locked(context):
    """locked main program, called only if lock was aqcuired successfully

    @param context: Connection context
    """
    context['hydra_url'] = f"https://{context['server']}/"
    context['headers'] = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'User-Agent': 'hydrascraper.py v1.0'
    }

    handled = get_handled(context['handled_file'])

    projects = get_projects(context)
    projects = list(filter(context['re_p'].match, projects))
    if DEBUG:
        print("Selected projects: ", projects)

    jobsets = {}
    for proj in projects:
        jobsets[proj] = get_jobsets(context, proj)

    for proj in projects:
        jobsets[proj] = list(filter(context['re_js'].match, jobsets[proj]))
        if DEBUG:
            print(f"{proj} selected jobsets: {jobsets[proj]}")

    for project in projects:
        for jobset in jobsets[project]:
            handled += handle_jobset(context, project, jobset, handled)

    update_handled(context['handled_file'], handled)


def json_e(context):
    """Enable JSON output in context

    @param context: Connection context
    """
    context['json_en'] = True
    if DEBUG:
        print("JSON enabled")


def debug_e(_):
    """Set global debug flag"""
    global DEBUG
    DEBUG = 1
    print("Debug enabled")


def hp_e(context):
    """Set hidden projects flag in context

    @param context: Connection context
    """
    context['hid_proj'] = True
    if DEBUG:
        print("Including hidden projects")


def dp_e(context):
    """Set disabled projects flag in context

    @param context: Connection context
    """
    context['dis_proj'] = True
    if DEBUG:
        print("Including disabled projects")


def hj_e(context):
    """Set hidden jobsets flag in context

    @param context: Connection context
    """
    context['hid_jobset'] = True
    if DEBUG:
        print("Including hidden jobsets")


def dj_e(context):
    """Set disabled jobsets flag in context

    @param context: Connection context
    """
    context['dis_jobset'] = True
    if DEBUG:
        print("Including disabled jobsets")


def main(argv):
    """Main function

    @param argv: Command line parameters
    """
    global DEBUG
    # Set debug if set in environment
    DEBUG = convert_int(os.getenv("DEBUG"))

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
        send_help()

    context['server'] = argv[0]

    regexes = []
    for i in [0, 1]:
        try:
            # Create regular expression objects of project and jobset strings
            regexes.append(re.compile(argv[i + 1]))
        except re.error as error:
            if error.pos is not None:
                print(argv[i + 1], file=sys.stderr)
                print(" " * error.pos + "^", file=sys.stderr)
            print(f"Regular expression error: {error.msg}", file=sys.stderr)
            sys.exit(1)

    context['re_p'] = regexes[0]
    context['re_js'] = regexes[1]
    context['handled_file'] = argv[3]
    context['action'] = argv[4]

    if len(argv) > 5:
        # Process options
        for i in range(5, len(argv)):
            func = argfu.get(argv[i], None)
            if func is not None:
                func(context)
            else:
                print(f"Invalid argument: {argv[i]}", file=sys.stderr)
                sys.exit(1)

    lock = filelock.FileLock(f"{argv[3]}.lock")
    try:
        lock.acquire(timeout=0)
        main_locked(context)

    except filelock.Timeout as timeout:
        if DEBUG:
            print(f"Unable to get lock {timeout.lock_file}")
            print("If no other hydrascrapers are running, "
                  "check permissions and/or delete the lock file")

    except PermissionError as perm_error:
        print(
            f"Could not aquire {argv[3]}.lock: {perm_error.strerror}", file=sys.stderr)

    finally:
        lock.release()


# Run main when executed from command line
if __name__ == "__main__":
    main(sys.argv[1:])
