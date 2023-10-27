"""
# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------




# Aiming to be used with Hydra (Nixos) builder for Ghaf project https://github.com/tiiuae/ghaf

# Activates Hydra (Ghaf docker based Hydra build system) to build new open Pull Requests
#(for the main repo under observations)
#
# Rebuilds still open (and previously built) PR if there has been new changes for that PR
# Uses Ghaf build tools from https://github.com/tiiuae/ci-public

# Can be used in service mode (polling frequently changes) or cherrypicking some wished open PR
# Keeps internal recoed which open PRs or changed PRs have been allready processed
# (given Hydra build commands ok)
#
#
"""


# pylint: disable=invalid-name # code written and variables named before lint usage decided
# pylint: disable=line-too-long # vscode with max 140 used
# pylint: disable=superfluous-parens # using parenthesis in if clauses
# pylint: disable=consider-using-with # intentional open file usage (no with)

import os
import sys
import argparse
import json
from collections import defaultdict
# pylint: disable=unused-import # tool cant handle urlib import
import urllib.request
from urllib.request import Request, urlopen

import copy
import time
from datetime import datetime
import subprocess
import schedule
from github import Github
from aiohttp.web_routedef import options


###########################################################################################
# Global needed configurations, see example setenv.sh file for settings these
############################################################################################

# Github related settings
TOKENFILE = ""  # "KEEP TOKENFILE PRIVATE, NOT TO BE STORED PUBLIC GIT, used to access Github repo for PR observations
TESTREPO = None  # Repo under PR observations
TESTPR = ""  # f"https://api.github.com/repos/{TESTREPO}/pulls"
ORGANIZATION = None  # required Github organization membership before building PR proceeds
# local file to store handled (built) PRs by their Github ID
BUILDPRSFILE = None
# local file to store builds done for open, allready built, but PR having changes being made
BUILDCHANGEDPRSFILE = None

# CLI command (Ghaf inhouse public tool) to manage Hydra operations
HYDRACTL = None
EXT_PORT = None  # Hybdra port dedicated for this POC build server
SERVER = None  # Hydra build server to be commanded
RUNDELAY = None  # minutes to wait before next execution of this script

__version__ = "0.73300"

# HYDRACTL_USERNAME and HYDRACTL_PASSWORD env variables (Hydra admin account). DO NOT STORE TO PUBLIC GIHUB
# Use for example local .sh file which exports them in shell when sourced

# Global commandline options

DRYRUNMODE = None
VERBOSEMODE = None
SERVICEMODE = None
CHERRYPICKEDPR = None


#########################################################################################################
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def GetChangePRData(pr, counter, myChangedfile, changetime):
    """
    Check if detected change in PR is a new one or has been allready built
    In case a new one, update database file (also if new change for open PR is detected)
    """

    # myChangedfile = ""
    print("")
    pr = str(counter)
    myChangedfile.seek(0)  # we need to read from start
    print(
        f"----- Changed PR numbers and change times from the DB file:{BUILDCHANGEDPRSFILE} ----------")
    foundnewtime = 0
    PRCount = 0
    FilePRNumbers = []
    ContentOfFilePRNumber = []

    myChangedfile.seek(0)
    for one_line in myChangedfile:
        PRCount = PRCount+1

        if (VERBOSEMODE is not None):
            print(one_line)
        # get runtime copy for possible changes
        ContentOfFilePRNumber.append(one_line)
    PRCount = PRCount-1  # fictional first value
    if (VERBOSEMODE is not None):
        print(
            f"------- Existing PRs with done change builds:{PRCount} ----------------")

    myChangedfile.seek(0)
    for one_line in myChangedfile:
        values = one_line.strip().split(",")
        readPR = values[0]
        readChangetime = values[1:]
        if (readPR == pr):
            FilePRNumbers.append(pr)

            if (changetime in readChangetime):
                print("Changetime found from PR built changes list")
            else:
                print("Found new changed time for this PR")
                foundnewtime = 1

# pylint: disable=no-else-return # returning intentionally
    if (pr in FilePRNumbers and foundnewtime == 0):
        print("No new PRs nor existing PRs with new changes found. No actions needed")
        return "NO"
    elif (pr in FilePRNumbers and foundnewtime > 0):
        print("Existing PRs with new changes found")
        print("Going to update changed PRs file!")
        addline = pr+","+changetime

        for index, item in enumerate(ContentOfFilePRNumber):
            if item.startswith(pr):
                matching_index = index
                print(f"Internal matching_index:{matching_index}")
                break
        if (matching_index is not None):
            ContentOfFilePRNumber[matching_index] = addline
        else:
            print("Internal: Can't change PR change time list")
            return "ERROR"

        myChangedfile = open(BUILDCHANGEDPRSFILE, "w", encoding='utf-8')

        for line in ContentOfFilePRNumber:  # write whole "changed PRs build" file again.
            print(f"Writing line:{line}")
            niceline = line+"\n"

            if (DRYRUNMODE is not None):
                print("!!!Dryrun mode, not going to do actions!!!")
            else:
                myChangedfile.write(niceline)

            myChangedfile = open(BUILDCHANGEDPRSFILE, "a", encoding='utf-8')
        return "YES"

    elif (pr not in FilePRNumbers):
        print(
            f"New PR:{pr}with changes found. Cleaned changetime:{changetime}")
        print("Going to update changed PRs file!")
        addline = pr+","+changetime
        ContentOfFilePRNumber.append(addline)

        myChangedfile = open(BUILDCHANGEDPRSFILE, "w", encoding='utf-8')
        for line in ContentOfFilePRNumber:  # write whole "changed PRs build" file again.
            niceline = line+"\n"
            if (DRYRUNMODE is not None):
                print("!!!Dryrun mode, not going to do actions!!!")
            else:
                myChangedfile.write(niceline)

            myChangedfile = open(BUILDCHANGEDPRSFILE, "a", encoding='utf-8')
        return "YES"

    return "DONE"


#########################################################################################
def CheckChangedPR(pr, repo, counter):
    """
    Check if PR (still open) has been changed since creation time
    """
    print(f"Checking PR:{pr}")
    pr = repo.get_pull(counter)
    CREATED = pr.created_at
    commits = pr.get_commits()
    # Sort the commits by the commit timestamp in descending order
    sorted_commits = sorted(
        commits, key=lambda c: c.commit.committer.date, reverse=True)
    if (VERBOSEMODE is not None):
        print(f"Found commits:{sorted_commits}")
    # Get the timestamp of the most recent commit
    CHANGED = sorted_commits[0].commit.committer.date

    print(f"CREATED:{CREATED}")
    print(f"CHANGED:{CHANGED}")

    time_diff_mins = (CHANGED - CREATED).total_seconds() / 60
    print(f"Time difference in minutes:{time_diff_mins}")

# pylint: disable=no-else-return # returning intentionally
    if (time_diff_mins > 10):
        print("Possible change in open PR detected, may require rebuilding")

        return "YES", CHANGED
    else:
        print("No changes for open PR detected")
        return "NO", ""

#########################################################################################
# pylint: disable=too-many-arguments
def PRBuilding(data, ErroCounter, g, org, counter, myfile, tbd_list, timetoken):
    """
    If PR creator is in defined Github membership, initate Hydra build definition actions
    """

    # parse PR info (from Github JSON)
    SOURCE = "NONE"
    TARGET = "NONE"
    SOURCE_REPO = "NONE"
    ErroCounter = 0
    print("")
    try:
        print(f"==> SOURCE PR BRANCH:{data['head']['ref']}")
        SOURCE = data["head"]["ref"]
    except KeyError:
        print("ERROR: no head ref found")
        ErroCounter = ErroCounter+1

    try:
        print(f"==> TARGET BRANCH (like main/master):{data['base']['ref']}")
        TARGET = data["base"]["ref"]
        if (TARGET == "main"):
            print("==> OK target(main) repo")
        else:
            print("ERROR: source repo is not main")
            ErroCounter = ErroCounter+1
    except KeyError:
        print("no base ref found")
    try:
        print(f"==> SOURCE REPO:{data['head']['repo']['html_url']}")
        SOURCE_REPO = data["head"]["repo"]["html_url"]
    except KeyError:
        print("ERROR:no source repo info found")
        ErroCounter = ErroCounter+1

    USER = data["user"]["login"]
    user = g.get_user(USER)

    if (org.has_in_members(user)):
        print(
            f"---> The user '{USER}' is a member of the organization '{ORGANIZATION}'.")
        if (counter in tbd_list):
            print(f"------> Handling PR number:{counter}")
            if (ErroCounter == 0):

                PRActions(SOURCE, counter, TARGET, myfile,
                          USER, SOURCE_REPO, timetoken)

            else:
                print("Errors in PR data from Github, not doing build activities")
    else:
        print(
            f"The user: {USER} is not a member of the organization {ORGANIZATION}")
        print("No build activities done")
    print("--------------------------------------------------------------------------------------------------")


##########################################################################################
# pylint: disable=too-many-locals
def PRActions(SOURCE, PR, TARGET, myfile, USER, SOURCE_REPO, timetoken):
    """
    Construct Hydra build command from PullRequests data (Using Ghaf inhouse CLI command)
    Record handled PR info to local db file
    """

    OK_CMDEXE_COUNTER = 0
    print("")
    print(
        f"Construct Hydra(for project tiiuae/ghaf) build job set for branch:{SOURCE}")

    if (VERBOSEMODE is not None):
        print(f"--> Target main branch:{TARGET}")
        print(f"--> Source branch:{SOURCE}")
        print(f"--> Source repo:{SOURCE_REPO}")
        print(f"--> PR number:{PR}")
        print(f"--> HYDRACTL command location used:{HYDRACTL}")
        print(f"--> Hydra port:{EXT_PORT}")
        print(f"--> Hydra server:{SERVER}")
        print(f"--> User:{USER}")
        print(f"--> Timetoken:{timetoken}")
        print("")
    DESCRIPTION = "\"PR:"+str(PR)+" User:"+USER + \
        " Repo:"+SOURCE_REPO+" Branch:"+SOURCE+"\""  # kept format intentionally

    if (len(timetoken) == 0):
        PROJECT = f"{USER}X{SOURCE}"
    else:
        PROJECT = f"{USER}X{SOURCE}X{timetoken}"

    # two phased convertings got this item usage working
    PROJECT = PROJECT.encode('ascii', errors='ignore')
    # Then convert it from bytes back to a string using:
    PROJECT = PROJECT.decode()

    FLAKE = "git+"+SOURCE_REPO+"/?ref="+SOURCE  # kept format intentionally
    if (len(timetoken) == 0):
        JOBSET = f"{SOURCE}X{PR}"
    else:
        JOBSET = f"{SOURCE}X{PR}X{timetoken}"

    if (VERBOSEMODE is not None):
        print(f"--> Hydra PROJECT:{PROJECT}")
        print(f"--> Hydra DESCRIPTION:{DESCRIPTION}")
        print(f"--> Hydra FLAKE:{FLAKE}")
        print(f"--> Hydra JOBSET:{JOBSET}")
    APCOMMAND = f"python3 {HYDRACTL} {SERVER}  AP --project {PROJECT} --display {DESCRIPTION}"
    AJCOMMAND = f"python3 {HYDRACTL} {SERVER} AJ --description {DESCRIPTION} --check 300 --type flake --flake {FLAKE} -s enabled --jobset {JOBSET} --project {PROJECT}"
    if (VERBOSEMODE is not None):
        print("")
        print(f"Created Hydra CLI APCOMMAND:{APCOMMAND}")
        print("")
        print(f"Created Hydra CLI AJCOMMAND:{AJCOMMAND}")
    DONE = PR  # write PR number to db file if both CMD exections are ok
    DONE = str(DONE)+"\r\n"  # intentionally kept format

    # NOTE: As executing commands from Python file failed (Hydra jobset creation) and using same commands were ok from shell
    # saving commands to file and executing the content from the read file
    # this is temp solution for this POC only

    cmdfile1 = open("cmdfile1", "w", encoding='utf-8')
    # cmdfile1.seek(0) # only if mode a used
    cmdfile2 = open("cmdfile2", "w", encoding='utf-8')
    # cmdfile2.seek(0)
    FIRSTLINE = "#!/bin/bash"+"\r\n"  # intentionally kept format

    cmdfile1.write(FIRSTLINE)
    cmdfile1.write(APCOMMAND)

    cmdfile2.write(FIRSTLINE)
    cmdfile2.write(AJCOMMAND)

    cmdfile1.close()
    cmdfile2.close()

    cmd1 = open("cmdfile1", "r", encoding='utf-8')
    APline1 = cmd1.read()
    rc, _out, err = ExeCMD(APline1)

    if (rc != 0):
        print(f"Command execution error:{rc}")
        print(f"Error message:{err}")
    else:
        print("OK command execution")
        OK_CMDEXE_COUNTER += 1

    time.sleep(2)
    cmd2 = open("cmdfile2", "r", encoding='utf-8')
    AJline2 = cmd2.read()
    rc, _out, err = ExeCMD(AJline2)
    if (rc != 0):
        print(f"Command execution error:{rc}")
        print(f"Error message:{err}")
    else:
        print("OK command execution")
        OK_CMDEXE_COUNTER += 1

    if (OK_CMDEXE_COUNTER == 2):
        if (len(timetoken) == 0):
            print(
                f"2 correct CMD executions,NEW build, going to record PR:{PR} as done deed")
            if (DRYRUNMODE is not None):
                print("!!!Dryrun mode, not going to do actions!!!")
            else:
                myfile.write(DONE)
        else:
            print(
                f"2 correct CMD executions, CHANGED PR build, going to record PR:{PR} with CHANGE time:{timetoken} to own db file")
    else:
        print("-------------------------------------------------------------------------------")
        print(
            f"ERROR ===> CMD executions errors found, NOT marking PR:{PR} as done")
        print("-------------------------------------------------------------------------------")

    # clean temp commandfiles
    os.remove("./cmdfile1")
    os.remove("./cmdfile2")
    time.sleep(2)

    print("*******************************************************************************************************")


##############################################################
def ExeCMD(commandLine):
    """
    Execute given command string and return system feedback
    """

    print("------------------------------------------------------------------------------------------")
    print(f"Executing command:{commandLine}")
    print("------------------------------------------------------------------------------------------")

# pylint: disable=no-else-return # returning intentionally
    if (DRYRUNMODE is not None):
        print("!!! Dryrun mode, not doing actions !!!")
        return (42, "dryrun mode", "dryrun mode")

    else:
        sp = subprocess.Popen(commandLine,
                              shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        rc = sp.wait()
        out, err = sp.communicate()

        return rc, out, err


##########################################################################################
def Finder():
    """
    Check if any new (not built) pull requests exists in defined repo (fro main branch
    """

    print("------------------------------------------------------------------------------------------")

    #########################################################################
    # Authorization to Github
    # Tokenfile used to provide token for observed Github Repo access
    # DO NOT STORE TOKENFILE TO GITHUB, KEEP IT PRIVATE
    #

    file_exists = os.path.exists(TOKENFILE)
    if (file_exists):
        file = open(TOKENFILE, "r", encoding='utf-8')
        config_array = file.read().split()
        githubtoken = str(config_array[0])
    else:
        print(f"No Github tokenfile found, check:{TOKENFILE}")
        githubtoken = None

    g = Github(githubtoken)
    repo = g.get_repo(TESTREPO)
    org = g.get_organization(ORGANIZATION)
    pulls = repo.get_pulls(state='open', sort='created', base='main')

    ##########################################################################
    # Get all open PRs into a dictionary for data processing
    i = 0
    open_prs = defaultdict(lambda: "OFF")
    print(f"------ All open PullRequest for repo: {TESTREPO} -------")
    for pull in pulls:
        print(pull)
        open_prs.update({pull.number: "ON"})
        i = i+1

    if (i == 0):
        print("No open PRs found, exiting")
        sys.exit(4)
    ####################################################################################
    # Read allready built PRs from disk, initialize possible empty bookkeeping files
    #
    done_prs = defaultdict(lambda: "NONE")
    myfile = open(BUILDPRSFILE, "a+", encoding='utf-8')
    myChangedfile = open(BUILDCHANGEDPRSFILE, "a+", encoding='utf-8')

    # add fictional done PR number to an empty file in order to keep logic running
    if (os.stat(BUILDPRSFILE).st_size == 0):
        print("No done PRs found, adding fictional PR number to an empty file")
        FICTIONALPR = 123456789
        FICTIONALPR = str(FICTIONALPR)+"\r\n"
        myfile.seek(0)
        myfile.write(FICTIONALPR)

    # add fictional changed PR number (and timetoken) to an empty file in order to keep logic running
    if (os.stat(BUILDCHANGEDPRSFILE).st_size == 0):
        print("No done PRs file found, adding fictional PR number and change time to an empty file")
        FICTIONALPR = 123456789
        FICTIONALCHANGETIME = "2020-02-02-23-00-00"
        # kept format intentionally
        FICTIONALCHANGEPR = str(FICTIONALPR)+","+FICTIONALCHANGETIME+"\r\n"
        myChangedfile.seek(0)
        myChangedfile.write(FICTIONALCHANGEPR)
    ##########################################################################################################

    # a+ adds fd to end of file, for appends, we need to read from start
    myfile.seek(0)
    print(f"------Built PR numbers from the DB file: {BUILDPRSFILE}------")
    for one_pr_number in myfile:
        if (VERBOSEMODE is not None):
            print(str(one_pr_number), end='')
        done_prs[int(one_pr_number)] = "DONE"

    print("------ Checking which open PRs are new and require building ------")
    # shallow copies are iterared over as defaultdict changes dict size when default value must be returned
    copy_done_prs = copy.copy(done_prs)
    copy_open_prs = copy.copy(open_prs)
    tbd_list = []
    counter = 1
    ###############################################################################
    # Process all repo's open pull requests
    processed_pr = []
    ErroCounter = 0
    for newPr in copy_open_prs:

        url = str(TESTPR)+"/"+str(newPr)  # kept format intentionally
        with urlopen(url) as response:
            body = response.read()
        data = json.loads(body)
        print("###########################################################################################################################")
        print("==> PR:"+url)

        if (CHERRYPICKEDPR is not None):
            if (CHERRYPICKEDPR == newPr):
                print(f"===> To be cherry picked PR found:{newPr}")
            else:
                print(
                    f"Skipping this one, trying to cherry pick PR:{CHERRYPICKEDPR}")
                continue

        print(f"==> CHECKING ---> SOURCE PR BRANCH: {data['head']['ref']}")

        counter = newPr  # not anymore running counter, but the actual open PR numbers
        for _doneline in copy_done_prs:

            # check duplicate PRs in db file
            # pylint: disable=no-else-break # breaking intentionally
            if (counter in processed_pr):
                print(f"Processed PRs:{processed_pr}")
                print(
                    f"---> Duplicate PR found in db file: {counter} skipping to next one!")
                print(
                    "--------------------------------------------------------------------------------------------------")
                break

            elif (open_prs[counter] == "ON" and done_prs[counter] == "DONE"):
                print(f"==> OLD PR in PR list, has been built:{counter}")

                print("Checking if this (still open) PR has been changed")
                pr = repo.get_pull(counter)
                answer, changetime = CheckChangedPR(pr, repo, counter)
                if (answer == "YES"):
                    print(f"PR changed, timetoken in use:{changetime}")

                    processed_pr.append(counter)
                    if (counter not in tbd_list):
                        tbd_list.append(counter)
                    else:
                        print("not adding")

                    # hydra doesnt like spaces in arguments, nor :
                    changeTimeCleaned = str(changetime).replace(" ", "-")
                    changeTimeCleaned = changeTimeCleaned.replace(":", "-")
                    if (VERBOSEMODE is not None):
                        print("Cleaned (book keeping) timetoken:" +
                              changeTimeCleaned)

                    answer = GetChangePRData(
                        pr, counter, myChangedfile, changeTimeCleaned)
                    if (answer == "YES"):
                        # SOURCE=data["head"]["ref"]
                        print(
                            f"==> CHECKING ---> SOURCE PR BRANCH:{data['head']['ref']}")

                        PRBuilding(data, ErroCounter, g, org, counter,
                                   myfile, tbd_list, changeTimeCleaned)
                    else:
                        print("")
                    break

                else:
                    print("No PR changes, no actions needed")
                    processed_pr.append(counter)
                    break
                print(
                    "--------------------------------------------------------------------------------------------------")
            elif (open_prs[counter] == "ON" and done_prs[counter] == "NONE"):
                print(f"==> NEW PR, going to build this:{counter}")
                processed_pr.append(counter)
                if (counter not in tbd_list):
                    tbd_list.append(counter)
                else:
                    print("not adding")

                timetoken = ""
                PRBuilding(data, ErroCounter, g, org, counter,
                           myfile, tbd_list, timetoken)
                break

            elif (open_prs[counter] == "OFF" and done_prs[counter] == "DONE"):
                print(f"==> OLD done PR:{counter}")
                processed_pr.append(counter)
                break


###################################################################################################################################
def GetEnv(variable):
    """
    Check that needed env variables are defined
    """

    definedVariable = os.getenv(variable)
    if (definedVariable is None and DRYRUNMODE is None):
        print(f"No {variable} env variable defined", file=sys.stderr)
        print("Check example setenv.sh file....Exiting now!!")
        sys.exit(3)
    else:

        definedVariable = str(definedVariable)
        if (VERBOSEMODE is not None):
            print(f"Set env variable:{variable} as {definedVariable}")
        else:
            definedVariable = str(definedVariable)
        return definedVariable


###################################################################################################################################
# pylint: disable=unused-argument
def main(argv):
    """ Main. Check parameters
    """

# pylint: disable=global-statement # used intentionally
    global CHERRYPICKEDPR
    global VERBOSEMODE
    global DRYRUNMODE
    global SERVICEMODE
    global TOKENFILE, TESTREPO, ORGANIZATION, BUILDPRSFILE, HYDRACTL, BUILDCHANGEDPRSFILE, EXT_PORT, SERVER, RUNDELAY, TESTPR

    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    print("----------------------------------------------------------------------------------------")
    print(f"---------- Execution started:{formatted_time}---------------")
    print("----------------------------------------------------------------------------------------")

    parser = argparse.ArgumentParser(
        description="Github PullRequest Hydra builder activator",


        epilog='''
    "Needs some env variables, see code for comments and setenv.sh as an example setter"
    ''')

    parser.add_argument('-v', help='Check Github open PRs and activate Ghaf Hydra build',
                        action='version', version=f"Version:{__version__}  ")
    parser.add_argument("-d", help='Dry run mode', metavar="dry")
    parser.add_argument('-t', help='Verbose, talking, mode', metavar="verbose")
    parser.add_argument('-s', help='Service mode, runtime delays in secs',
                        metavar="service", type=int, nargs=1)
    parser.add_argument('-p', help='Cherry pick PR number, ignore others',
                        metavar="cherrypick", type=int, nargs=1)

    args = parser.parse_args()

    VERBOSEMODE = args.t or None
    DRYRUNMODE = args.d or None
    SERVICEMODE = args.s or None

    if (args.s):
        SERVICEMODE = args.s[0]
    if (args.p):
        CHERRYPICKEDPR = args.p[0]

    if (VERBOSEMODE is not None):
        print("Verbose mode selected")
    if (DRYRUNMODE is not None):
        print("!!! Dryrun mode selected, no actions taken !!!")
    if (SERVICEMODE):
        print(f"Service mode selected with runtime delay:{SERVICEMODE}")
    if (CHERRYPICKEDPR is not None):
        print(f"Checking only PR:{CHERRYPICKEDPR} skpping other PRs")

    # pylint: disable=unused-variable
    username = GetEnv("HYDRACTL_USERNAME")  # env check only
    # pylint: disable=unused-variable
    passu = GetEnv("HYDRACTL_PASSWORD")  # env check only
    TOKENFILE = GetEnv("TOKENFILE")
    print(f"GOT Tokenfile file:{TOKENFILE}")
    TESTREPO = GetEnv("TESTREPO")
    ORGANIZATION = str(GetEnv("ORGANIZATION"))
    BUILDPRSFILE = GetEnv("BUILDPRSFILE")
    BUILDCHANGEDPRSFILE = GetEnv("BUILDCHANGEDPRSFILE")
    HYDRACTL = GetEnv("HYDRACTL")
    EXT_PORT = GetEnv("EXT_PORT")
    SERVER = f"http://localhost:{EXT_PORT}"
    RUNDELAY = GetEnv("RUNDELAY")
    TESTPR = f"https://api.github.com/repos/{TESTREPO}/pulls"

    print("")
    print(f"TESTPR:{TESTPR}")
    print(f"Tokenfile file:{TOKENFILE}")
    print(f"Build PRs db file:{BUILDPRSFILE}")
    print(f"Build and rebuild PRs due changes db file: {BUILDCHANGEDPRSFILE}")
    print(f"Observing Github repo (main) PRs: {TESTREPO}")
    print(
        f"Organization participation required for PR building:{ORGANIZATION}")
    print(f"Using Hydra build server:{SERVER}")
    print(f"Assuming Hydra CLI command to be:{HYDRACTL}")
    print("Only PRs to main branch are processed")
    print("")

    if (SERVICEMODE):
        print("Service mode starting!")
        schedule.every(RUNDELAY).minutes.do(Finder)
        while True:
            schedule.run_pending()
            time.sleep(SERVICEMODE)
    else:
        print("Running command just once")
        Finder()


#######################################################
# Entry point
if __name__ == "__main__":
    main(sys.argv[1:])
