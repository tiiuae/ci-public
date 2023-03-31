#!/bin/bash

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

check_file_exists () {
    if ! [ -s "$1" ]; then
        echo "Error: File not found: \"$1\"" >&2
        exit 1
    fi
}

strip_ansi_colors () {
    sed -e 's/\x1b\[[0-9;]*m//g'
}

echo "Arguments:"
echo "  vulns_csv_baseline_path: '$vulns_csv_baseline_path'"
echo "  buildID: '$buildID'"
echo "  resultsPath: '$resultsPath'"

export PATH=$PATH:/nix/var/nix/profiles/default/bin/

set -x # debug
set -u # treat unset variables as an error and exit
pwd
outdir="$(echo "$resultsPath"/"$buildID"/ | sed 's/ //')"
check_file_exists "$vulns_csv_baseline_path"
check_file_exists "$outdir"

printf '\n\n---\nVerify vulns.csv for current build exists\n---\n'
vulns_current_path="$outdir/vulns.runtime__$buildID.csv"
check_file_exists "$vulns_current_path"

# Compare csv files $vulns_csv_baseline_path and $vulns_current_path
printf '\n\n---\nRun csvdiff\n---\n'
nix run github:tiiuae/ci-public?dir=csvdiff#csvdiff -- "$vulns_csv_baseline_path" "$vulns_current_path" |& strip_ansi_colors
check_file_exists "csvdiff.csv"

printf '\n\n---\nListing fixed vulnerabilities (compared to %s)\n---\n' "$vulns_csv_baseline_path"
# Fixed vulns: vulnerabilities that were labeled 'left_only' by csvdiff
(head -n1 csvdiff.csv; grep "left_only" csvdiff.csv) >vulns_fixed.csv
nix-shell -p csvkit --run 'csvlook vulns_fixed.csv'
# Check if vulns_fixed.csv actually contains some data, not only the header row
if tail +2 vulns_fixed.csv | grep -qE '.*'; then
    cp vulns_fixed.csv "$outdir/vulns_fixed.runtime__$buildID.csv"
else
    printf 'No fixed vulnerabilities in this build\n\n'
fi

printf '\n\n---\nListing new vulnerabilities (compared to %s)\n---\n' "$vulns_csv_baseline_path"
# New vulns: vulnerabilities that were labeled 'right_only' by csvdiff
(head -n1 csvdiff.csv; grep "right_only" csvdiff.csv) >vulns_new.csv
nix-shell -p csvkit --run 'csvlook vulns_new.csv'
# Check if vulns_new.csv actually contains some data, not only the header row
if tail +2 vulns_new.csv | grep -qE '.*'; then
    cp vulns_new.csv "$outdir/vulns_new.runtime__$buildID.csv"
else
    printf 'No new vulnerabilities in this build\n\n'
fi
