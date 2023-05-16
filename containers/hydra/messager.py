#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.slackclient ])"
#
#
# This Slack messager needs 1) Slack authorization app token 2) slack channel to be messaged in a configuration file (in this order)
# When Slack app is being created, the authorization token is given by the system. Please see Slack info how to create Slack apps.
#
# DO NOT STORE SLACK CONFIGURATION FILE TO GITHUB EVER. IT INCLUDES ACCESST TOKEN. ADD IT MANUALLY TO /containers/hydra directory FOR DOCKER
# IMAGE BUILDING. 
#
import os,sys,argparse
import slack   
from slack import WebClient
from slack.errors import SlackApiError


__version__ = u"0.73300"
MESSAGETEXT=u""
  

parser = argparse.ArgumentParser(description="Send message to Slack channel (as a Slack app)",
    
    
 epilog="""
    
    Configuration file content: line0: slack app token, line1:slack channel to be messaged
    Keep token (and configuration file) in safe. Do not store to git.
    
    python3 messager.py  -m "TEXT FOR SLACKCHANNEL" -f CONFIGURATION FILE"""  
    
)
parser.add_argument('-v', help='Send Slack message', action='version',version="Version:{0}   mika.nokka1@gmail.com ,  MIT licenced ".format(__version__) )
parser.add_argument("-f",help='<Slack configuration file>',metavar="file")
parser.add_argument("-m",help='<Slack message>',metavar="message")
   
args = parser.parse_args()       
SLACKMESSAGE = args.m or ''
SLACKCONFIGURATIONFILE= args.f or ''
     
# quick old-school way to check needed parameters
if (SLACKMESSAGE=='' or  SLACKCONFIGURATIONFILE=='' ):
        print("\n---> MISSING ARGUMENTS!!\n ")
        parser.print_help()
        sys.exit(2)
     
file_exists = os.path.exists(SLACKCONFIGURATIONFILE)

if (file_exists):

        print ("Slack configuration file exists. Going to slack",file=sys.stderr)
        file = open(SLACKCONFIGURATIONFILE, "r")
        config_array=file.read().split()
        slackchannel=str(config_array[1])
        slacktoken=str(config_array[0])
        try:
            client = slack.WebClient(token=slacktoken)
            client.chat_postMessage(channel=slackchannel, text=SLACKMESSAGE)

        except Exception as e:
            print(("Slacking failed! Check your channel name?, error: %s" % e))
            sys.exit(1)
    
        
else:
        print ("No Slack configuration file found. Doing nothing",file=sys.stderr)    