#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie
# ------------------------------------------------------------------------
# Script for adding a project and a jobset into Hydra

# ------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------
import requests
import os
import sys
import json

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------

# Server url will also be used as the referring page
ref = ""

# Extra headers for HTTP requests
headers = {'Accept': 'application/json, text/javascript, */*'}


# ------------------------------------------------------------------------
# Prints an error message and exits
# ------------------------------------------------------------------------
def perror(txt, code=1):
    print(txt, file=sys.stderr)
    sys.exit(code)


# ------------------------------------------------------------------------
# Show usage help
# ------------------------------------------------------------------------
def help():
    txt = """
Usage: python3 hydractl.py <url> <project> <project description> \\
       <jobset> <jobset description> <nix file> <interval> \\
       <1st input> <1st input source> [2nd input] [2nd input source] ...

                url = Server URL (Please include a forward slash in the end)
            project = Name of the project
project description = Project description
             jobset = Name of the jobset
 jobset description = Jobset description
           nix file = Nix file that will be the basis of the build (The nix
                      file must reside in the first input source given)
           interval = Polling interval
          1st input = Name of the first input
   1st input source = Source URL of the first input (If you also specify a
                      branch, please note that you'll have to space separate
                      and quote the string)
     2nd input etc. = Follow 1st input specification above

Credentials for logging into hydra need to be provided in the environment
variables HYDRACTL_USERNAME and HYDRACTL_PASSWORD or in the "credentials.txt"
file which is in the same directory as the script itself. First line should
contain the username and the second line the password. If you use the
credentials file, please make sure it's only readable by the user running the
script.

Example: python3 hydractl.py https://vedenemo.dev/ my-project "Test project" \\
         my-jobset "Test jobset" release.nix 0 \\
         spectrum "https://github.com/tiiuae/spectrum x86_nuc" \\
         nixpkgs "https://github.com/tiiuae/nixpkgs-spectrum x86_nuc"
"""
    perror(txt, 0)


# ------------------------------------------------------------------------
# Login to hydra server
# ------------------------------------------------------------------------
def hydra_login(user, passwd, ses):
    url = f"{ref}login"
    data = {"username": user, "password": passwd}

    return ses.post(url, data, headers=headers)


# ------------------------------------------------------------------------
# Logout from hydra server
# ------------------------------------------------------------------------
def hydra_logout(ses):
    url = f"{ref}logout"
    return ses.post(url, headers=headers)


# ------------------------------------------------------------------------
# Main application
# ------------------------------------------------------------------------
def main(argv):
    global headers
    global ref

    # Get credentials from the environment if possible
    username = os.getenv("HYDRACTL_USERNAME")
    password = os.getenv("HYDRACTL_PASSWORD")

    # If either one was missing, try the credentials file
    if username == None or password == None:
        # Find credentials file from the directory of the script
        # Note: Credentials file should be only readable by the user we are running as
        credfile = os.path.dirname(os.path.realpath(__file__)) + '/credentials.txt'

        # Read credentials
        try:
            with open(credfile, 'r') as sf:
                username = sf.readline().strip()
                password = sf.readline().strip()
        except IOError:
            perror(f"Unable to read {credfile}")

    # Check for empty username or password
    if username == '' or password == '':
        perror("Malformed credentials")

    # If too few parameters or odd number of parameters, show help
    if len(argv) < 10 or len(argv) % 2 == 1:
        help()

    # Get parameters into more readable variables
    ref = argv[1]
    project = argv[2]
    projdesc = argv[3]
    jobset = argv[4]
    jobdesc = argv[5]
    nix = argv[6]
    interval = argv[7]
    inputs = argv[8:]

    # Set referer in HTTP headers, hydra requires this
    headers['Referer'] = ref

    #print(f"ref={ref}")
    #print(f"project={project}")
    #print(f"projdesc={projdesc}")
    #print(f"jobset={jobset}")
    #print(f"jobdesc={jobdesc}")
    #print(f"nix={nix}")
    #print(f"interval={interval}")
    #print(f"inputs={inputs}")

    # Create a session (session keeps track of cookies etc.)
    s = requests.session()

    # Try to login into hydra
    r = hydra_login(username, password, s)
    if  r.status_code != 200:
        print(f"Login failed: {r.status_code}", file=sys.stderr)
        perror(r.content,2)

    # Setup project data
    projectdata = {
        "declarative": {
            "file": "",
            "type": "bitbucketpulls",
            "value": ""
        },
        "enabled": "on",
        "visible": "on",
        "name": project,
        "displayname": project,
        "description": projdesc,
        "homepage": "",
        "owner": username
    }

    # Convert from dictionary to JSON
    jsondata = json.dumps(projectdata, indent=None)

    # Try to create the project
    r = s.put(f"{ref}project/.new", jsondata, headers=headers)
    if r.status_code != 201:
        print(f"Project put result: {r.status_code}", file=sys.stderr)
        perror(r.content, 3)

    # Setup jobset data
    jobsetdata={
        "inputs": {},
        "enabled": "1",
        "visible": "on",
        "name": jobset,
        "type": "0",
        "description": jobdesc,
        "flake": "",
        "nixexprpath": nix,
        "nixexprinput": inputs[0],
        "checkinterval": interval,
        "schedulingshares": "100",
        "keepnr":"3"
    }

    # Setup given inputs in jobset data
    i = 0
    while i < len(inputs):
        jobsetdata['inputs'][inputs[i]] = {"type": "git", "value": inputs[i+1]}
        i = i + 2

    # Convert dictionary to JSON
    jsondata = json.dumps(jobsetdata, indent=None)

    # Try to create the new jobset
    r = s.put(f"{ref}jobset/{project}/.new", jsondata, headers=headers)
    if r.status_code != 201:
        print(f"Jobset put result: {r.status_code}", file=sys.stderr)
        perror(r.content, 4)

    # Logout
    r = hydra_logout(s)
    if  r.status_code != 204:
        print(f"Logout failed: {r.status_code}", file=sys.stderr)
        perror(r.content, 5)

    perror("Success", 0)


# ------------------------------------------------------------------------
# If this was invoked directly from command line, call the main function
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv)
