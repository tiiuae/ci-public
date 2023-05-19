#!/usr/bin/env pipenv-shebang
# ------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
# Script for adding a projects and a jobsets into Hydra

# Credentials for logging into hydra need to be provided in the environment
# variables HYDRACTL_USERNAME and HYDRACTL_PASSWORD or in the "credentials.txt"
# file which is in the same directory as the script itself. First line should
# contain the username and the second line the password. If you use the
# credentials file, please make sure it's only readable by the user running the
# script.

# Examples:
#   hydractl.py https://hydra.vedenemo.dev/ AP -p my-project -D "Test project"
#   hydractl.py https://hydra.vedenemo.dev/ AJ -p my-project -j my-jobset \\
#     -D "Test jobset" -e release.nix spectrum -c 0 \\
#     -I spectrum git "https://github.com/tiiuae/spectrum x86_nuc" false \\
#     -I nixpkgs git "https://github.com/tiiuae/nixpkgs-spectrum x86_nuc" false


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
headers = {'Accept': 'application/json'}

# Default nix expression if not given
def_expr = ['default.nix','--FIRST--INPUT--']

# Strings that represent true values
true_strs = ['1', 't', 'true', 'on', 'y', 'yes', 'enabled']

# Strings that represent false values
false_strs = ['0', 'f', 'false' ,'off', 'n', 'no', 'disabled']

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

jobset_states = ['disabled', 'enabled', 'one-shot', 'one-at-a-time']

jobset_types = ['legacy', 'flake']

# Modified from argparse.BooleanOptionalAction
class MyBooleanOptionalAction(argparse.Action):
    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith('--'):
                option_string = '--not-' + option_string[2:]
                _option_strings.append(option_string)

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(namespace, self.dest, not option_string.startswith('--not-'))

    def format_usage(self):
        return ' | '.join(self.option_strings)


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
# Handle 'AP' add project command and 'MP' modify project command
# args = Dictionary of info got from arguments
# returns processed dictionary
# ------------------------------------------------------------------------
def handle_project(args :dict):
    if args['CMD'][0] != 'D':
        i = args['declarative']
        if i != None:
            i[1] = i[1].lower()
            if not i[1] in input_types.keys():
                print(f"Invalid input type: {i[1]}\n", file=sys.stderr)
                list_input_types()
                perror("")

            args['declarative'] = {'file': i[0], 'value': i[2], 'type': i[1]}

        if args['CMD'][0] == 'A' and args['displayname'] == None:
            args['displayname'] = args['project']

    args['name'] = args['project']
    del args['project']


# ------------------------------------------------------------------------
# Handle 'AJ' add jobset command
# args = Dictionary of info got from arguments
# returns processed dictionary
# ------------------------------------------------------------------------
def handle_jobset(args :dict) -> dict:
    if args['CMD'][0] != 'D':
        i = args['inputs']
        t = args['type']

        if t == 'flake':
            if i != None:
                perror("No inputs may be defined when when flake type is used")

            if args['expression'] != def_expr and args['expression'] != None:
                perror("Cannot define Nix expression when flake type is used")

            if args['flake'] == "" or args['flake'] == None:
                perror("Flake URI must be specified when flake type is used")

            args['nixexprpath'] = ""
            args['nixexprinput'] = ""
            args['type'] = 1
        elif t == 'legacy':
            if i == None:
                perror("At least one input is required when legacy type is used")

            if args['flake'] != "" and args['flake'] != None:
                perror("Cannot define flake URI when legacy type is used")

            if args['expression'] == def_expr:
                args['expression'] = [def_expr[0], i[0][0]]

            args['nixexprpath'] = args['expression'][0]
            args['nixexprinput'] = args['expression'][1]
            args['flake'] = ""

            args['type'] = 0
        else:
            if args['expression'] != None:
                perror('Cannot define Nix expression if legacy type not defined')
            if args['flake'] != None:
                perror('Cannot define fĺake URI if flake type not defined')
            args['nixexprpath'] = None
            args['nixexprinput'] = None

        if i != None:
            args['inputs'] = {}
            expinpfound = False
            for inp in i:
                if inp[0] == args['nixexprinput']:
                    expinpfound = True
                inp[1] = inp[1].lower()
                if not inp[1] in input_types.keys():
                    print(f"Invalid input type: {inp[1]}\n", file=sys.stderr)
                    list_input_types()
                    perror("")
                if inp[3].lower() in true_strs:
                    args['inputs'][inp[0]] = {"type": inp[1], "value": inp[2], "emailresponsible": True}
                elif inp[3].lower() in false_strs:
                    args['inputs'][inp[0]] = {"type": inp[1], "value": inp[2]}
                else:
                    perror(f"Invalid boolean value: {inp[3]}")

            if not expinpfound:
                perror(f"Invalid input in Nix expression: {args['nixexprinput']}")

        if args['enabled'] != None:
            # Convert enabled string to (0 - 3)
            args['enabled'] = jobset_states.index(args['enabled'])

        del args['expression']


# ------------------------------------------------------------------------
# Merge object info changes with downloaded info
# ------------------------------------------------------------------------
def merge(cmd: str, base: dict, args: dict):
    if cmd[1] == 'P':
        # For some very weird reason 'hidden' is the variable when
        # reading project information but it's 'visible' when writing
        # project information
        base['visible'] = base.get('hidden', False) == False

    for key, val in args.items():
        if val == None:
                args[key] = base.get(key)


# ------------------------------------------------------------------------
# Parse command line arguments
# argv = Command line arguments (including program name)
# user = username
# returns parsed and verified info dictionary
# ------------------------------------------------------------------------
def parse_args(argv, user :str) -> dict:
    parser = argparse.ArgumentParser(description = "Create/modify Hydra projects and jobsets",
                                     epilog = "Use command 'hydractl.py - AP|AJ|MP|MJ|DP|DJ -h' for more help")

    parser.add_argument('URL',
                        help = "Hydra server URL")
    subparsers = parser.add_subparsers(help="Sub command help")

    parser_cmds=[{'CMD': 'AP', 'help': "Add a project"},
                 {'CMD': 'AJ', 'help': "Add a jobset"},
                 {'CMD': 'MP', 'help': "Modify a project"},
                 {'CMD': 'MJ', 'help': "Modify a jobset"},
                 {'CMD': 'DP', 'help': "Delete a project"},
                 {'CMD': 'DJ', 'help': "Delete a jobset"}]

    for pcmd in parser_cmds:
        subparser = pcmd['parser'] = subparsers.add_parser(pcmd['CMD'], help=pcmd['help'])
        subparser.add_argument('--CMD', default=pcmd['CMD'], help=argparse.SUPPRESS)

        # Project id is required for all commands
        subparser.add_argument('-p', '--project',
            required = True,
            help = "Project identifier")

        addition = pcmd['CMD'][0] == 'A'
        projectop = pcmd['CMD'][1] == 'P'
        object = "project" if projectop else "jobset"

        if not projectop:
            # Any jobset command requires jobset id parameter
            subparser.add_argument('-j', '--jobset',
                required = True,
                dest = 'name',
                help = "Jobset identifier")

        if pcmd['CMD'][0] != 'D':
            # Common options for addition1 and modification commands
            subparser.add_argument('--visible',
                action = MyBooleanOptionalAction,
                default = True if addition else None,
                help = f"{object.capitalize()} visibility (default visible)")
            subparser.add_argument('-D', '--description',
                default = "" if addition else None,
                nargs = 1,
                help = f"{object.capitalize()} description (default blank)")
            subparser.add_argument('--drun',
                action = MyBooleanOptionalAction,
                default = None,
                dest = 'enable_dynamic_run_command',
                help = "Enable/disable dynamic runcommand hooks (default: disabled)")
            if pcmd['CMD'][1] == 'P':
                # Project specific options
                subparser.add_argument('--enabled',
                    action = MyBooleanOptionalAction,
                    default = True if addition else None,
                    help = "State of the project (default enabled)")
                subparser.add_argument('-d', '--display',
                    default = None,
                    nargs = 1,
                    dest = 'displayname',
                    help = "Project display name (default = project id)")
                subparser.add_argument('-u', '--homepage',
                    default = "" if addition else None,
                    nargs = 1,
                    help = "Project homepage (default blank)")
                subparser.add_argument('-o', '--owner',
                    default = user if addition else None,
                    nargs = 1,
                    help = "Project owner (default from credentials)")
                subparser.add_argument('-I', '--input',
                    nargs = 3,
                    default = None,
                    dest = 'declarative',
                    metavar = ('FILE', 'TYPE', 'VALUE'),
                    help = "Declarative input")
            else:
                # Jobset specific options
                subparser.add_argument('-s', '--state',
                    choices = jobset_states,
                    default = jobset_states[1] if addition else None,
                    nargs = 1,
                    type = str.lower,
                    dest = 'enabled',
                    help = f"State of the {object} (default {jobset_states[1]})")
                subparser.add_argument('-t', '--type',
                    choices = jobset_types,
                    default = jobset_types[0] if addition else None,
                    type = str.lower,
                    help = f"Jobset type (default {jobset_types[0]})")
                subparser.add_argument('-f', '--flake',
                    nargs = 1,
                    default = "" if addition else None,
                    help = "Flake URI (default blank)")
                subparser.add_argument('-e', '--expression',
                    metavar = ('EXPR','INPUT'),
                    nargs = 2,
                    default = def_expr if addition else None,
                    help = "Nix expression ('default.nix' in first input by default)")
                subparser.add_argument('-c', '--check',
                    default = '0' if addition else None,
                    nargs = 1,
                    dest = 'checkinterval',
                    metavar = 'INTERVAL',
                    help = "Check interval in seconds (default '0' = no checking)")
                subparser.add_argument('-S', '--shares',
                    default = '100' if addition else None,
                    nargs = 1,
                    dest = 'schedulingshares',
                    help = "Scheduling shares (default 100)")
                subparser.add_argument('--emailnotify',
                    action = MyBooleanOptionalAction,
                    default = False if addition else None,
                    dest = 'enableemail',
                    help = "Email notification (default don't notify)")
                subparser.add_argument('--email',
                    nargs = 1,
                    default = "" if addition else None,
                    dest = 'emailoverride',
                    metavar = 'EMAIL',
                    help = "Email override for notifications (default blank)")
                subparser.add_argument('-n', '--nreval',
                    nargs = 1,
                    default = '1' if addition else None,
                    dest = 'keepnr',
                    help = "Number of evaluations to keep (default '1')")
                subparser.add_argument('-I', '--input',
                    action = 'append',
                    nargs = 4,
                    dest = 'inputs',
                    metavar = ('NAME','TYPE','VALUE','NOTIFY'),
                    help = "Inputs (You may define several)")

    # Do the actual parsing
    res = parser.parse_args(argv[1:])

    args = vars(res)

    # remove lists "around" singular arguments (except inputs)
    # Note: iterating directly the dictionary somehow ignored the list types
    # That's why this is iterating through the keys
    for k in args.keys():
        if k != "inputs" and type(args[k]) == list and len(args[k]) == 1:
            args[k] = args[k][0]

    if args['CMD'][1] == 'P':
        handle_project(args)
    elif args['CMD'][1] == 'J':
        handle_jobset(args)
    else:
        perror(f"Invalid command: {args['CMD']}")

    return args


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

    ref = args['URL'].removesuffix('/') + '/'
    del args['URL']

    cmd = args['CMD']
    del args['CMD']

    # Set referer in HTTP headers, hydra requires this
    headers['Referer'] = ref

    # Create a session (session keeps track of cookies etc.)
    s = requests.session()

    # Try to login into hydra
    r = hydra_login(username, password, s)
    if  r.status_code != 200:
        print(f"Login failed: {r.status_code}", file=sys.stderr)
        perror(r.content, 2)

    if cmd[1] == 'P':
        if cmd[0] == 'A':
            url = f'{ref}project/.new'
        else:
            url = f'{ref}project/{args["name"]}'
    else:
        if cmd[0] == 'A':
            url = f'{ref}jobset/{args["project"]}/.new'
        else:
            url = f'{ref}jobset/{args["project"]}/{args["name"]}'

    if cmd[0] == 'D':
        r = s.delete(url, headers = headers)
        if r.status_code != 200:
            print(f"Delete result: {r.status_code}", file = sys.stderr)
            perror(r.content, 3)
    else:
        if cmd[0] == 'M':
            r = s.get(url, headers = headers)
            if r.status_code != 200:
                print(f"Get result: {r.status_code}", file = sys.stderr)
                perror(r.content, 3)
            base = json.loads(r.content)

            merge(cmd, base, args)

        # Disabling some options happens by not sending an enabling value
        # Setting value to false won't do what you expect (hydra weirdness)
        if cmd[1] == 'P':
            if not args['enabled']:
                del args['enabled']
        else:
            if not args['enableemail']:
                del args['enableemail']

        if not args['visible']:
            del args['visible']

        # You may not even set this to false, if the feature is not enabled in hydra
        if args['enable_dynamic_run_command'] != True:
            del args['enable_dynamic_run_command']

        jsondata = json.dumps(args, indent = None)

        r = s.put(url, jsondata, headers = headers)
        if r.status_code not in [200, 201]:
            print(f"Put result: {r.status_code}", file = sys.stderr)
            perror(r.content, 3)

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
