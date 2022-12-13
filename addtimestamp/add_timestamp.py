# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Ville-Pekka Juntunen <ville-pekka.juntunen@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie
# ------------------------------------------------------------------------
# Script for adding "Post processing done" unix timestamp to <buildID>.json.
# ------------------------------------------------------------------------
import sys
import json
import time


# ------------------------------------------------------------------------
# Main program
# ------------------------------------------------------------------------
def main(argv):
    jsonFile = argv[0] + "/" + argv[1]
    timestamp = int( time.time() )
    try:
        with open(jsonFile) as f:
            data = json.load(f)
            data["Post processing done at"] = str(timestamp)
            json.dump(data, open(jsonFile, "w"), indent = 4)
        print("Post processing timestamp added to .json file")
    except:
         print("Something went wrong adding post process timestamp to .json file")


# ------------------------------------------------------------------------
# Run main when executed from command line
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[1:])
