#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.slackclient ])"
#
# SPDX-FileCopyrightText: 2023-2024 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------
""""
# Hydra Slack messaging script
#
# Prints given message to configured Slack channel(s) (standalone mode)
# When used with Hydra postbuild, Slacks to given channels major Hydra build information data
#
# Postbuild (user of this script) assumes it is stored to store/home/confs/ in host side.
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

parser = argparse.ArgumentParser(description="Send build result message to Slack channel(s) (as a Slack app)",


                                 epilog="""

    Configuration file content:
    line0: slack app token
    line1: slack channel status for bad news (failed builds) (ON/OFF)  channel name
    line2: slack channel status for good news (ok builds) (ON/OFF)  channel name

    Example configuration file:

    line0: 1300073000ABC
    line1: ON bad_news_slack_channel
    line2: OFF good_news_slack_channel

    --> Slack only failed builds info

    Keep token (and configuration file) in safe. Do not store to git.

    Usage example:

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

slacktoken = badcommand = badslackchannel = goodcommand = goodslackchannel = None

if file_exists:
    print("Slack configuration file exists. Going try to do the messaging", file=sys.stderr)

    try:
        file = open(SLACKCONFIGURATIONFILE, "r", encoding="utf-8")
        config_array = file.read().splitlines()

        if len(config_array) == 3:
            slacktoken = str(config_array[0])

            if (len(config_array[1].split()) != 2 or len(config_array[2].split()) != 2):
                raise ValueError(
                    "Invalid file format.Expecting: ON/OFF channelname")

            badcommand, badslackchannel = (
                str(config_array[1]).split(maxsplit=1))
            if (badcommand not in {"ON", "OFF"}):
                raise ValueError(
                    "Invalid command in the second line. Use 'ON' or 'OFF'.")

            goodcommand, goodslackchannel = (
                str(config_array[2]).split(maxsplit=1))
            if (goodcommand not in {"ON", "OFF"}):
                raise ValueError(
                    "Invalid command in the third line. Use 'ON' or 'OFF'.")
        else:
            print(
                f"Error in configuration file: {SLACKCONFIGURATIONFILE}. Did not find 3 lines of needed definitions")
            sys.exit(5)

        print(f"goodcommand: {goodcommand}, goodchannel: {goodslackchannel}")
        print(f"badcommand: {badcommand}, badchannel: {badslackchannel}")

    except ValueError as ve:
        print(f"Configuration error: {ve}", file=sys.stderr)
        sys.exit(6)

    except Exception as e:
        print(f"Error reading configuration file: {e}", file=sys.stderr)
        sys.exit(7)

else:
    print(
        f"Error: Slack configuration file not found at {SLACKCONFIGURATIONFILE}", file=sys.stderr)
    sys.exit(4)


# TESTING WITHOUT BUILD AS STANDALONE COMMAND: set buildStatNbr 0 (ok build) or >1 (failed build)
# buildStatNbr=1

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
        buildStatNbr = int(buildstatus)
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

if (buildStatNbr == 0):
    doit = goodcommand
    slackchannel = goodslackchannel
else:
    doit = badcommand
    slackchannel = badslackchannel

if (doit == "ON"):
    try:
        client = slack.WebClient(token=slacktoken)
        client.chat_postMessage(channel=slackchannel, text=SLACKMESSAGE)
        print(f"Asked Slack to process our message (channel: {slackchannel})")

    except Exception as e:
        print(f"Slacking failed! Check your channel name?, error: {e}")
        sys.exit(1)
else:
    print(f"Slacking not ON for channel: {slackchannel}. Not going to Slack!")
