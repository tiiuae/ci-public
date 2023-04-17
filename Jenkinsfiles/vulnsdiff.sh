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
# We use csvdiff to compare the vulnerabilities between the specified builds.
# The command-line arguments '--cols=vuln_id,package' and '--ignoredups'
# deserve an explanation:
#
#   csvdiff command-line argument '--cols=vuln_id,package' indicates that
#   we only want to consider differences in columns 'vuln_id' and 'package'.
#   '--ignoredups' indicates we want to ignore the differences in the count
#   of same vulnerabilities (as identified by the specified column names).
#
#   Following example illustrates this:
#
#   left:
#     vuln_id      | package | version
#    --------------+---------+---------
#     CVE-2023-123 | openssh | 9.1p1
#     CVE-2023-123 | openssh | 9.1p2
#
#   right:
#     vuln_id      | package | version
#    --------------+---------+---------
#     CVE-2023-123 | openssh | 9.2
#
#   If we compared the above examples 'left' and 'right' with
#   csvdiff without '--cols=vuln_id,package', csvdiff would consider all
#   the rows unique due to different version numbers. Therefore, we would
#   incorrectly end up reporting all the vulnerabilities in 'left' as
#   fixed, and the one vulnerability in 'right' as new vulnerability.
#
#   With '--cols=vuln_id,package' but without '--ignoredups', csvdiff would
#   count the number of unique entries by vuln_id and package and report
#   the difference, that is, that 'left' had two entries of
#   {CVE-2023-123,openssh}, whereas, 'right' only had one.
#
#   With both '--cols=vuln_id,package' and '--ignoredups', csvdiff correctly
#   considers all the vulnerabilities in 'left' and 'right' as the same as
#   well as ignores the difference in the count of unique entries in 'left'
#   and 'right'.
#
nix run github:tiiuae/ci-public?dir=csvdiff#csvdiff -- "$vulns_csv_baseline_path" "$vulns_current_path" --ignoredups --cols=vuln_id,package |& strip_ansi_colors
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
