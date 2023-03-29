#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=invalid-name, protected-access

""" Python script for comparing two csv files """

import sys
import csv
import logging
import argparse
import pathlib
from colorlog import ColoredFormatter, default_log_colors
import pandas as pd


################################################################################


def _getargs():
    """Parse command line arguments"""
    desc = (
        "This tool compares two csv files. Exit status is 0 if the csv files "
        "LEFT_CSV and RIGHT_CSV include the same rows (in any order). In all "
        "other cases, the exit status is 1."
    )
    epil = "Example: csvdiff /path/to/left.csv /path/to/right.csv"
    parser = argparse.ArgumentParser(description=desc, epilog=epil)
    helps = "Path to first csv file"
    parser.add_argument("LEFT_CSV", help=helps, type=pathlib.Path)
    helps = "Path to second csv file"
    parser.add_argument("RIGHT_CSV", help=helps, type=pathlib.Path)
    helps = "Path to output file (default: ./csvdiff.csv)"
    parser.add_argument("--out", nargs="?", help=helps, default="csvdiff.csv")
    helps = (
        "Ignore duplicate rows in both LEFT_CSV and RIGHT_CSV. "
        "By default, this script counts the duplicate rows on each side "
        "when comparing the CSV files and reports a difference if the number "
        "of duplicate entries for each row does not match. With this option, "
        "the script removes non-unique rows from both LEFT_CSV "
        "and RIGHT_CSV before comparing them."
    )
    parser.add_argument("--ignoredups", help=helps, action="store_true")
    helps = "Set the debug verbosity level between 0-2 (default: --verbose=1)"
    parser.add_argument("--verbose", help=helps, type=int, default=1)
    return parser.parse_args()


###############################################################################

LOG = logging.getLogger(__name__)

###############################################################################

# utils


def _setup_logging(verbosity):
    """Setup logging with specified verbosity"""
    log_levels = {
        0: logging.CRITICAL,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    max_verbosity = max(log_levels.keys())
    level = log_levels[min(verbosity, max_verbosity)]
    if level <= logging.DEBUG:
        logformat = (
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(filename)s:%(funcName)s():%(lineno)d "
            "%(message)s"
        )
    else:
        logformat = "%(log_color)s%(levelname)-8s%(reset)s %(message)s"

    default_log_colors["INFO"] = "fg_bold_white"
    default_log_colors["DEBUG"] = "fg_bold_white"
    formatter = ColoredFormatter(logformat, log_colors=default_log_colors)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    LOG.addHandler(stream)
    LOG.setLevel(level)


def df_to_csv_file(df, name):
    """Write dataframe to csv file"""
    df.to_csv(
        path_or_buf=name, quoting=csv.QUOTE_ALL, sep=",", index=False, encoding="utf-8"
    )
    LOG.info("Wrote: %s", name)


def df_from_csv_file(name):
    """Read csv file into dataframe"""
    LOG.debug("Reading: %s", name)
    try:
        df = pd.read_csv(name, keep_default_na=False, dtype=str)
        df.reset_index(drop=True, inplace=True)
        return df
    except pd.errors.ParserError:
        LOG.fatal("Not a csv file: '%s'", name)
        sys.exit(1)


###############################################################################


def _csv_diff(path_left, path_right, ignoredups=False):
    """Return the diff of two csv files"""
    # Read csv file into pandas dataframe
    df_left = df_from_csv_file(path_left)
    df_right = df_from_csv_file(path_right)
    if ignoredups:
        df_left.drop_duplicates(keep="first", inplace=True)
        df_right.drop_duplicates(keep="first", inplace=True)
    # Error out if colum names don't match
    cols_diff = set(df_left.columns) ^ set(df_right.columns)
    if cols_diff:
        LOG.fatal(
            "Mismatch in column names\n\n  left: %s\n  right:%s",
            list(df_left.columns),
            list(df_right.columns),
        )
        sys.exit(1)
    if df_left.empty:
        LOG.fatal("No rows in LEFT_CSV")
        sys.exit(1)
    if df_right.empty:
        LOG.fatal("No rows in RIGHT_CSV")
        sys.exit(1)
    uids = list(df_left.columns)
    # Add 'count' column that indicates the count of duplicates by 'uids'
    df_left_uidg = df_left.groupby(by=uids).size().reset_index(name="count")
    df_right_uidg = df_right.groupby(by=uids).size().reset_index(name="count")
    # Outer join to compare left and right dataframes
    df_diff = pd.merge(
        left=df_left_uidg,
        right=df_right_uidg,
        how="outer",
        indicator=True,
        on=uids,
        suffixes=("_left", "_right"),
    )
    # Add column 'diff' that classifies the diff status
    df_diff["diff"] = df_diff.apply(_classify_row, axis=1)
    if LOG.level <= logging.DEBUG:
        df_to_csv_file(df_diff, "df_diff_raw.csv")
    # Remove temporary columns we added above
    df_diff.drop(["count_left", "count_right", "_merge"], inplace=True, axis=1)
    # Drop duplicate rows
    df_diff.drop_duplicates(keep="first", inplace=True)
    # Sort rows ignoring case
    df_diff.sort_values(by=uids, inplace=True, key=lambda col: col.str.lower())
    return df_diff


def _classify_row(row):
    """
    Given a row item with columns 'count_left', 'count_right', and '_merge',
    return a string that classifies the row diff status
    """
    LOG.debug(dict(row))
    if row._merge != "both":
        # Row is either 'left_only' or 'right_only'
        return row._merge
    if row.count_left > row.count_right:
        # Row is in both, but there are more non-unique items in 'left'.
        # We simply classify such rows as 'left_only'
        return "left_only"
    if row.count_right > row.count_left:
        # Row is in both, but there are more non-unique items in 'right'.
        # We simply classify such rows as 'right_only'
        return "right_only"
    # Otherwise the row is in both left and right
    return "both"


def _report_diff(df_diff):
    df_common = df_diff[df_diff["diff"] == "both"]
    if not df_common.empty:
        LOG.info("Number of common rows: %s", df_common.shape[0])
    df_left_only = df_diff[df_diff["diff"] == "left_only"]
    if not df_left_only.empty:
        LOG.warning("Number of LEFT_ONLY rows: %s", df_left_only.shape[0])
    df_right_only = df_diff[df_diff["diff"] == "right_only"]
    if not df_right_only.empty:
        LOG.warning("Number of RIGHT_ONLY rows: %s", df_right_only.shape[0])
    return df_left_only.empty and df_right_only.empty


###############################################################################


def main():
    """main entry point"""
    args = _getargs()
    _setup_logging(args.verbose)
    if not args.LEFT_CSV.exists():
        LOG.fatal("Invalid LEFT_CSV path: '%s'", args.LEFT_CSV)
        sys.exit(1)
    if not args.RIGHT_CSV.exists():
        LOG.fatal("Invalid RIGHT_CSV path: '%s'", args.RIGHT_CSV)
        sys.exit(1)
    left_csv = args.LEFT_CSV.as_posix()
    right_csv = args.RIGHT_CSV.as_posix()
    LOG.info("Comparing 'LEFT_CSV=%s' 'RIGHT_CSV=%s'", left_csv, right_csv)
    df_diff = _csv_diff(left_csv, right_csv, args.ignoredups)
    diff = not bool(_report_diff(df_diff))
    df_to_csv_file(df_diff, args.out)
    sys.exit(int(diff))


################################################################################

if __name__ == "__main__":
    main()

################################################################################
