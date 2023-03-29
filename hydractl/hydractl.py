#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2022-2023 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022-2023 Unikie
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# ------------------------------------------------------------------------
# Script for adding a projects and a jobsets into Hydra

# Credentials for logging into hydra need to be provided in the environment
# variables HYDRACTL_USERNAME and HYDRACTL_PASSWORD or in the "credentials.txt"
# file which is in the same directory as the script itself. First line should
# contain the username and the second line the password. If you use the
# credentials file, please make sure it's only readable by the user running the
# script.

# Examples:
#   hydractl.py https://hydra.vedenemo.dev/ AP -i my-project -D "Test project"
#   hydractl.py https://hydra.vedenemo.dev/ AJ -p my-project -i my-jobset \\
#     -D "Test jobset" -e release.nix spectrum -c 0 \\
#     -I spectrum git "https://github.com/tiiuae/spectrum x86_nuc" off \\
#     -I nixpkgs git "https://github.com/tiiuae/nixpkgs-spectrum x86_nuc" off


# ------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------
import requests
import os
import sys
import json
import argparse

# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------

# Server url will also be used as the referring page
ref = ""

# Extra headers for HTTP requests
headers = {'Accept': 'application/json, text/javascript, */*'}

# Default nix expression if not given
def_expr = ['default.nix','--FIRST--INPUT--']

# Strings that represent true values
true_strs = ['1', 'true', 'on', 'yes', 'enabled']

# Strings that represent false values
false_strs = ['0', 'false' ,'off', 'no', 'disabled']

# Hydra input types
input_types = {
    "bitbucketpulls": "Open BitBucket Pull Requests",
    "boolean": "Boolean",
    "build": "Previous Hydra build",
    "bzr": "Bazaar export",
    "bzr-checkout": "Bazaar checkout",
    "darcs": "Darcs checkout",
    "eval": "Previous Hydra evaluation",
    "git": "Git checkout",
    "github refs": "Open GitHub Refs",
    "githubpulls": "Open GitHub Pull Requests",
    "gitlabpulls": "Open Gitlab Merge Requests",
    "hg": "Mercurial checkout",
    "nix": "Nix expression",
    "path": "Local path or URL",
    "string": "String value",
    "svn": "Subversion export",
    "svn-checkout": "Subversion checkout",
    "sysbuild": "Previous Hydra build (same system)"
}


# ------------------------------------------------------------------------
# Prints an error message and exits
# txt = Error message
# code = optional exit code
# ------------------------------------------------------------------------
def perror(txt, code=1):
    print(txt, file=sys.stderr)
    sys.exit(code)


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
# List available input types
# ------------------------------------------------------------------------
def list_input_types():
    print("Available input types:", file=sys.stderr)
    for type in input_types.keys():
        print(f"{type:>20} = {input_types[type]}", file=sys.stderr)


# ------------------------------------------------------------------------
# Handle 'AP' add project command
# args = Dictionary of info got from arguments
# returns processed dictionary
# ------------------------------------------------------------------------
def handle_project(args :dict):
    i = args['input']
    if i != None:
        i[0] = i[0].lower()
        if not i[0] in input_types.keys():
            print(f"Invalid input type: {i[0]}\n", file=sys.stderr)
            list_input_types()
            perror("")
    if args['display'] == None:
        args['display'] = args['id']
    return args


# ------------------------------------------------------------------------
# Handle 'AJ' add jobset command
# args = Dictionary of info got from arguments
# returns processed dictionary
# ------------------------------------------------------------------------
def handle_jobset(args :dict) -> dict:
    i = args['input']
    args['type'] = args['type'].lower()
    t = args['type']

    if t == 'flake':
        if i != None:
            perror("No inputs may be defined when when flake type is used")

        if args['expression'] != def_expr:
            perror("Cannot define Nix expression when flake type is used")

        if args['flakeuri'] == "":
            perror("Flake URI must be specified when flake type is used")
    else:
        if i == None:
            perror("At least one input is required when legacy type is used")

        for inp in i:
            inp[1] = inp[1].lower()
            if not inp[1] in input_types.keys():
                print(f"Invalid input type: {inp[1]}\n", file=sys.stderr)
                list_input_types()
                perror("")
            inp[3] = inp[3].lower()
            if inp[3] in true_strs:
                inp[3] = 'on'
            elif inp[3] in false_strs:
                inp[3] = 'off'
            else:
                perror(f"Invalid boolean value: {inp[3]}")

        if args['expression'] == def_expr:
            args['expression'] = [def_expr[0], i[0][0]]

    return args


# ------------------------------------------------------------------------
# Parse command line arguments
# argv = Command line arguments (including program name)
# user = username
# returns parsed and verified info dictionary
# ------------------------------------------------------------------------
def parse_args(argv, user :str) -> dict:
    parser = argparse.ArgumentParser(description = "Create a Hydra projects and jobsets",
                                     epilog = "Use commands 'hydractl.py - AP -h' and 'hydractl.py - AJ -h' for more help")

    parser.add_argument('URL',
                        help = "Hydra server URL (please include trailing slash)")
    subparsers = parser.add_subparsers(help="Sub command help")
    prj_parser = subparsers.add_parser('AP', help="Add a project")
    js_parser = subparsers.add_parser('AJ', help="Add a jobset")

    prj_parser.add_argument('--CMD',
                            default = 'AP',
                            help = argparse.SUPPRESS)
    prj_parser.add_argument('-i', '--id',
                            required = True,
                            help = "Project identifier")
    prj_parser.add_argument('-s', '--state',
                            choices = ['enabled', 'disabled'],
                            default = 'enabled',
                            nargs = 1,
                            help = "State of the project (enabled by default)")
    prj_parser.add_argument('-H','--hidden',
                            action = 'store_false',
                            dest = 'visible',
                            help = "Make project hidden")
    prj_parser.add_argument('-V','--visible',
                            action = 'store_true',
                            dest = 'visible',
                            help = "Make project visible (default)")
    prj_parser.add_argument('-d', '--display',
                            default = None,
                            nargs = 1,
                            help = "Project display name (default = project id)")
    prj_parser.add_argument('-D', '--description',
                            default = "",
                            nargs = 1,
                            help = "Project description")
    prj_parser.add_argument('-p', '--homepage',
                            default = "",
                            nargs = 1,
                            help = "Project homepage")
    prj_parser.add_argument('-o', '--owner',
                            default = user,
                            nargs = 1,
                            help = "Project owner (default from credentials)")
    prj_parser.add_argument('--edrch',
                            action = 'store_true',
                            dest = 'edrch',
                            help = "Enable Dynamic RunCommand Hooks for Jobsets")
    prj_parser.add_argument('--ddrch',
                            action = 'store_false',
                            dest = 'edrch',
                            help = "Disable Dynamic RunCommand Hooks for Jobsets (default)")
    prj_parser.add_argument('-f', '--specfile',
                            default = "",
                            nargs = 1,
                            help = "Declarative spec file (Leave blank for non-declarative project configuration)")
    prj_parser.add_argument('-I','--input',
                            nargs = 2,
                            default = [list(input_types)[0], ''],
                            metavar = ('TYPE', 'VALUE'),
                            help = "Declarative input")

    js_parser.add_argument('--CMD',
                           default = 'AJ',
                           help = argparse.SUPPRESS)
    js_parser.add_argument('-p', '--project',
                           required = True,
                           help = "Parent project ID")
    js_parser.add_argument('-i', '--id',
                           required = True,
                           help = "Jobset identifier")
    js_parser.add_argument('-s', '--state',
                           choices = ['enabled', 'one-shot', 'one-at-a-time', 'disabled'],
                           default = 'enabled',
                           help = "State of the jobset (enabled by default)")
    js_parser.add_argument('-H','--hidden',
                           action = 'store_false',
                           dest = 'visible',
                           help = "Make jobset hidden")
    js_parser.add_argument('-V','--visible',
                           action = 'store_true',
                           dest = 'visible',
                           help = "Make jobset visible (default)")
    js_parser.add_argument('-t', '--type',
                           choices = ['flake', 'legacy'],
                           default = 'legacy',
                           help = "Jobset type (legacy by default)")
    js_parser.add_argument('-D', '--description',
                           default = "",
                           nargs = 1,
                           help = "Jobset description")
    js_parser.add_argument('-f', '--flakeuri',
                           nargs = 1,
                           default = "",
                           help = "Flake URI")
    js_parser.add_argument('-e', '--expression',
                           metavar = ('EXPR','INPUT'),
                           nargs = 2,
                           default = def_expr,
                           help = "Nix expression ('default.nix' in first input by default)")
    js_parser.add_argument('-c', '--check',
                           default = '0',
                           nargs = 1,
                           metavar = 'INTERVAL',
                           help = "Check interval in seconds ('0' by default = no checking)")
    js_parser.add_argument('-S', '--shares',
                           default = '100',
                           nargs = 1,
                           help = "Scheduling shares (100 by default)")
    js_parser.add_argument('--edrch',
                           action = 'store_true',
                           dest = 'edrch',
                           help = "Enable Dynamic RunCommand Hooks")
    js_parser.add_argument('--ddrch',
                           action = 'store_false',
                           dest = 'edrch',
                           help = "Disable Dynamic RunCommand Hooks (default)")
    js_parser.add_argument('--emailnotify',
                           action = 'store_true',
                           dest = 'email',
                           help = "Email notification (please use email override if you use this!)")
    js_parser.add_argument('--no-notify',
                           action = 'store_false',
                           dest = 'email',
                           help = "No email notifications (default)")
    js_parser.add_argument('--emailoverride',
                           nargs = 1,
                           default = "",
                           metavar = 'EMAIL',
                           help = "Email override for notifications")
    js_parser.add_argument('-n', '--nreval',
                           nargs = 1,
                           default = '1',
                           help = "Number of evaluations to keep ('1' by default)")
    js_parser.add_argument('-I', '--input',
                           action = 'append',
                           nargs = 4,
                           metavar = ('NAME','TYPE','VALUE','NOTIFY'),
                           help = "Inputs (You may define several)")

    # Do the actual parsing
    res = parser.parse_args(argv[1:])

    args = vars(res)

    # remove lists "around" singular arguments (except inputs)
    # Note: iterating directly the dictionary somehow ignored the list types
    # That's why this is iterating through the keys
    for k in args.keys():
        if k != "input" and type(args[k]) == list and len(args[k]) == 1:
            args[k] = args[k][0]

    if args['CMD'] == 'AP':
        return handle_project(args)
    elif args['CMD' ] == 'AJ':
        return handle_jobset(args)
    else:
        perror(f"Invalid command: {args['CMD']}")


# ------------------------------------------------------------------------
# Main application
# argv = command line parameters
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

    args = parse_args(argv, username)

    ref = args['URL']

    # Set referer in HTTP headers, hydra requires this
    headers['Referer'] = ref

    # Create a session (session keeps track of cookies etc.)
    s = requests.session()

    # Try to login into hydra
    r = hydra_login(username, password, s)
    if  r.status_code != 200:
        print(f"Login failed: {r.status_code}", file=sys.stderr)
        perror(r.content, 2)

    if args['CMD'] == 'AP':
        # Setup project data
        projectdata = {
            "declarative": {
                "file": args['specfile'],
                "type": args['input'][0],
                "value": args['input'][1]
            },
            "name": args['id'],
            "displayname": args['display'],
            "description": args['description'],
            "homepage": args['homepage'],
            "owner": args['owner'],
        }

        if args['state'] == 'enabled':
            projectdata['enabled'] = "on"

        if args['visible'] == True:
            projectdata['visible'] = "on"

        if args['edrch'] == True:
            projectdata['enable_dynamic_run_command'] = "on"

        # Convert from dictionary to JSON
        jsondata = json.dumps(projectdata, indent = None)

        # Try to create the project
        r = s.put(f"{ref}project/.new", jsondata, headers = headers)
        if r.status_code != 201:
            print(f"Project put result: {r.status_code}", file = sys.stderr)
            perror(r.content, 3)

    elif args['CMD'] == 'AJ':
        # Setup jobset data
        jobsetdata={
            "inputs": {},
            "enabled": "",
            "visible": "on" if args['visible'] == True else "off",
            "name": args['id'],
            "type": "0" if args['type'] == 'legacy' else "1",
            "description": args['description'],
            "flake": args['flakeuri'],
            "nixexprpath": "" if args['type'] == 'flake' else args['expression'][0],
            "nixexprinput": "" if args['type'] == 'flake' else args['expression'][1],
            "checkinterval": args['check'],
            "schedulingshares": args['shares'],
            "keepnr": args['nreval']
        }

        if args['state'] == 'disabled':
            jobsetdata['enabled'] = '0'
        elif args['state'] == 'one-shot':
            jobsetdata['enabled'] = '2'
        elif args['state'] == 'one-at-a-time':
            jobsetdata['enabled'] = '3'
        else:
            jobsetdata['enabled'] = '1'

        # Be sure to only enable, never to explicitly disable, this.
        # When one tries to set it to ANY value, hydra side parser
        # checks if these have been disabled on server or project
        # level, and complains if they are.
        if args['edrch'] == True:
            jobsetdata['enable_dynamic_run_command'] = 'true'

        if args['input'] != None:
            for inp in args['input']:
                # Setup given inputs in jobset data
                if inp[3] == "off":
                    jobsetdata['inputs'][inp[0]] = {"type": inp[1], "value": inp[2]}
                else:
                    jobsetdata['inputs'][inp[0]] = {"type": inp[1], "value": inp[2], "emailresponsible": "on"}

        # Convert dictionary to JSON
        jsondata = json.dumps(jobsetdata, indent = None)

        # Try to create the new jobset
        r = s.put(f"{ref}jobset/{args['project']}/.new", jsondata, headers = headers)
        if r.status_code != 201:
            print(f"Jobset put result: {r.status_code}", file = sys.stderr)
            perror(r.content, 4)
    else:
        perror("Somehow CMD was something unexpected", 1)

    # Logout
    r = hydra_logout(s)
    if  r.status_code != 204:
        print(f"Logout failed: {r.status_code}", file = sys.stderr)
        perror(r.content, 5)

    perror("Success", 0)


# ------------------------------------------------------------------------
# If this was invoked directly from command line, call the main function
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv)
