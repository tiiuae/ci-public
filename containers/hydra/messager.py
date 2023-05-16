#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.slackclient ])"
#
#


import os,sys,argparse
import slack   
from slack import WebClient
from slack.errors import SlackApiError



__version__ = u"0.73300"

MESSAGETEXT=u""
  

parser = argparse.ArgumentParser(description="Send message to Slack channel (as a Slack app)",
    
    
 epilog="""
    
    EXAMPLE:
    
    SLACKTOKEN env variable assumed to include Slack app token
    
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

print (SLACKCONFIGURATIONFILE)        
file_exists = os.path.exists(SLACKCONFIGURATIONFILE)

if (file_exists):

        print ("slack_config file exists. Going to slack",file=sys.stderr)
        file = open(SLACKCONFIGURATIONFILE, "r")
        config_array=file.read().split()
        slackchannel=str(config_array[1])
        slacktoken=str(config_array[0])
        #print ("content0:"+slacktoken,file=sys.stderr)
        #print ("content1:"+slackchannel,file=sys.stderr)
        #print (SLACKMESSAGE,file=sys.stderr)
        
        try:
            client = slack.WebClient(token=slacktoken)
            client.chat_postMessage(channel=slackchannel, text=SLACKMESSAGE)

        except Exception as e:
            print(("Slacking failed! Check your channel name?, error: %s" % e))
            sys.exit(1)
    
        
else:
        print ("No slack_config file found. Doing nothing",file=sys.stderr)    