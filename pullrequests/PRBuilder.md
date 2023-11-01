  Copyright 2023 TII (SSRC) and the Ghaf contributors
  <br>
  SPDX-License-Identifier: CC-BY-SA-4.0

# Ghaf Github Pull Request Hydra Builder
<br>
Builder for Ghaf project [https://github.com/tiiuae/ghaf](URL) Github Pull Requests

Uses Ghaf build tools & docs from [https://github.com/tiiuae/ci-public](URL) (assumes usage of Ghaf docker based Hydra build system)

Activates Hydra to build new open Pull Requests (for the main repo under observations) or allready built open PRs with new changes

Can be used in service mode (polling frequently repo changes) or cherry picking one open PR for building or just running once here and there

Keeps internal records for build PRs and rebuild changed PRs (building means commanding Hydra to initiate build for given PR branch and getting "ok" from Hydra)
<br>
<br>

## Needed python modules

- requests
- schedule
- (py)github
- aiohttp

E.g. to install to ubuntu system from debian packages:
> sudo apt install python3-schedule python3-github python3-aiohttp

E.g. to setup NixOS /etc/nixos/configuration.nix:
environment.systemPackages = with pkgs; [
  (python310.withPackages(ps: with ps; [ requests schedule pygithub aiohttp ]))
];

## USAGE
<br>
1) Setup Ghaf Hydra docker based build system
<br>
2) Set needed Hydra and PR tool env variables (see example setenv.sh and tool code for explanations)
<br>
3) (Optional) Create tokenfile to include your access token to repo for PR detections
<br>
4) Start (one off run) poller execution: python3 PollPr.py (use docker host , tools repo checkout in the host)
<br>
<br>
Editing "build" information files, one can manipulate which PR number is thought to be asked build or not
(set via env variables)
<br>

## CONFIGURATIONS (see example setenv.sh)
<br>
HYDRACTL_USERNAME="automation" ---> Hydra automation account
<br>
TOKENFILE="tokenfile" ---> token to access Github repo for these PR observations. If not present, anonymous access will be used
<br>
TESTREPO="tiiuae/ghaf" ---> Ghaf repo under PR observations
<br>
ORGANIZATION="tiiuae" ---> required Github organization membership before building PR proceeds
<br>
BUILDPRSFILE="pr2_data" ---> local file to store handled (as building) PRs by their Github ID
<br>
BUILDCHANGEDPRSFILE="pr2_changed_data" ---> local file for builds done for open (but build already initially) and changed PRs
<br>
HYDRACTL="../hydractl/hydractl.py" ---> Hydra CLI command location (Ghaf inhouse) to manage Hydra operations
<br>
EXT_PORT=3030 ---> Hybdra port dedicated for the build server (docker will expose this to the host)
<br>
RUNDELAY=30 ---> minutes to wait before next execution of this script (in service mode)

<br>
Set hydra automation password manually in order not to accidentically commiting it to public repo
<br>
export HYDRACTL_PASSWORD ="YOURSECRETPASSWORD"


## Commandline

Github PullRequest Hydra builder activator

options:
<br>
  -h, --help --> show this help message and exit
<br>
  -v --> Version
<br>
  -d on --> Dry run mode
<br>
  -t on --> Verbose, talking, mode
<br>
  -s MINS --> Service mode, runtime delays in mins
<br>
  -p PR --> Cherry pick given open PR number, ignore others


## Examples

PollPR.py --> run once
<br>
PollPr.py -d on --> Run once drymode, do not do any changes
<br>
PollPr.py -p 42 --> Ask Hydra to build PR42 (and if its build, check if any changes done for PR)
<br>
PollPr.py -s 60 --> Run every hour

#
