#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.slackclient ])"
#
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
""""
# Hydra Slack messaging script
#
# Prints given message to configured Slack channel with major hydra build
# information data
#
# Slack configuration file format:
# line1: Slack auth secret token (given when Slack application created)
# line2: Used Slack channel (Slack application must be installed for this channel for usage)
#
# Do not keep this auth file in version control system. Postbuild (user of this script) assumes
# it is stored to store/home/confs/ in host side.
#
#
# ------------------------------------------------------------------------
"""
import os
import sys
import argparse
import json
import slack
from slack import WebClient
from slack.errors import SlackApiError


__version__ = "0.73300"
MESSAGETEXT = ""


parser = argparse.ArgumentParser(description="Send message to Slack channel (as a Slack app)",


                                 epilog="""

    Configuration file content: line0: slack app token, line1:slack channel to be messaged
    Keep token (and configuration file) in safe. Do not store to git.

    python3 messager.py  -m "TEXT FOR SLACKCHANNEL" -f CONFIGURATION FILE"""

                                 )
parser.add_argument('-v', help='Send Slack message', action='version',
                    version=f"Version:{__version__}   mika.nokka1@gmail.com ,  MIT licenced ")
parser.add_argument("-f", help='<Slack configuration file>', metavar="file")
parser.add_argument("-m", help='<Slack message>', metavar="message")

args = parser.parse_args()
SLACKMESSAGE = args.m or ''
SLACKCONFIGURATIONFILE = args.f or ''

# quick old-school way to check needed parameters
if (SLACKMESSAGE == '' or SLACKCONFIGURATIONFILE == ''):
    print("\n---> MISSING ARGUMENTS!!\n ")
    parser.print_help()
    sys.exit(2)

file_exists = os.path.exists(SLACKCONFIGURATIONFILE)

if file_exists:

    SLACKMESSAGE = ""  # forming first message part here, not using passed argument

    print("Slack configuration file exists. Going to do the messaging", file=sys.stderr)
    file = open(SLACKCONFIGURATIONFILE, "r", encoding="utf-8")
    config_array = file.read().split()
    slackchannel = str(config_array[1])
    slacktoken = str(config_array[0])

    hydraserver = os.getenv("POSTBUILD_SERVER")
    if hydraserver is None:
        print("No Hydra server defined", file=sys.stderr)
        HYDRASERVER = ""
    else:
        HYDRASERVER = "\nHydra server:"+hydraserver

    hydradata = os.getenv("HYDRA_JSON")
    if hydradata is None:
        print("No Hydra JSON defined", file=sys.stderr)
    else:
        with open(hydradata) as jsonf:
            binfo = json.load(jsonf)
            # prettyinfo=json.dumps(binfo,indent=3)
            buildjob = str(binfo['job'])
            buildstatus = str(binfo['buildStatus'])
            buildnumber = str(binfo['build'])
            buildproject = str(binfo['project'])

            message_dict = {
                None: "False build! Did not finish, maybe evaluation failed ??",
                0: "OK build !!!",
                1: "Failed build, no other information !!!",
                2: "Dependency failed build !!!",
                3: "Aborted build !!!",
                4: "Cancelled by the user build !!!",
                5: "Failed build by undefined reason !!!",
                6: "Failed with output build !!!",
                7: "Timed out build !!!",
                8: "Failed build by undefined reason !!!",
                9: "Aborted build !!!",
                10: "Log size limit exceed failure build !!!",
                11: "Output size limit exceed build !!!"
            }

            SLACKMESSAGE = message_dict.get(int(
                buildstatus),  "Broken build for some undefined reason, maybe future error message ???")

            SLACKMESSAGE = SLACKMESSAGE+HYDRASERVER+"\nHydra build:" + \
                str(buildjob)+"\nStatus:"+buildstatus+"\nNumber:" + \
                buildnumber+"\nProject:"+buildproject

    try:
        client = slack.WebClient(token=slacktoken)
        client.chat_postMessage(channel=slackchannel, text=SLACKMESSAGE)

    except Exception as e:
        print(f"Slacking failed! Check your channel name?, error: {e}")
        sys.exit(1)


else:
    print("No Slack configuration file found. Doing nothing", file=sys.stderr)
