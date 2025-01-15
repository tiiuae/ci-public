#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access, too-many-locals
# pylint: disable=too-many-branches, too-many-statements

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
        "This tool compares two csv files writing the comparison result "
        "to a csv file '[OUT]', by default, 'csvdiff.csv'. The output file "
        "details the result of comparing the rows between LEFT_CSV "
        "and RIGHT_CSV, adding column 'diff' to the "
        "output file to report the comparison result for each row. "
        "Possible values for 'diff' column are: 'both', 'left_only', or "
        "'right_only' indicating whether the specific row was found from "
        "both files, only in the LEFT_CSV, or only in the RIGHT_CSV. "
        "Exit status is 1 if error occurred. In all other cases, the exit "
        "status is 0."
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
    helps = (
        "Comma-separated list of column names to use as basis for diff "
        "between the two files. By default, when this option is not "
        "specified, the csv files are compared across all column names. "
        "As an example `--cols=name,version,id` would compare the csv "
        "files based on data only on columns 'name', 'version', and 'id' "
        "discarding possible values on all other columns."
    )
    parser.add_argument(
        "--cols",
        help=helps,
        type=lambda s: [str(col) for col in s.split(",")],
        default=None,
    )
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
        LOG.fatal("Not a csv file '%s'", name)
        sys.exit(1)
    except pd.errors.EmptyDataError:
        LOG.fatal("No columns to parse from '%s'", name)
        sys.exit(1)


###############################################################################


def _csv_diff(path_left, path_right, ignoredups=False, cols=None):
    """Return the diff of two csv files"""
    # Read csv file into pandas dataframe
    df_left = df_from_csv_file(path_left)
    df_right = df_from_csv_file(path_right)
    if cols is not None:
        # Diff based on the given column names
        uids = list(set(cols))
        if not set(cols).issubset(df_left.columns):
            LOG.fatal("Not all column names %s in LEFT_CSV", cols)
            sys.exit(1)
        if not set(cols).issubset(df_right.columns):
            LOG.fatal("Not all column names %s in RIGHT_CSV", cols)
            sys.exit(1)
        if "diff" in uids:
            LOG.fatal("Reserved column name 'diff' can not be used as uid")
            sys.exit(1)
        LOG.info("Using column names %s as uid", uids)
    else:
        # Otherwise, diff based on all column names
        uids = list(df_left.columns)
        # Error out if column names between the two files don't match
        cols_diff = set(df_left.columns) ^ set(df_right.columns)
        if cols_diff:
            LOG.fatal(
                "Mismatch in column names\n\n  left: %s\n  right:%s",
                list(df_left.columns),
                list(df_right.columns),
            )
            sys.exit(1)
    if ignoredups:
        # Drop duplicates either by given column names or all column names if
        # ignoredups was requested
        dupsby = cols if cols else df_left.columns
        df_left.drop_duplicates(subset=dupsby, keep="first", inplace=True)
        df_right.drop_duplicates(subset=dupsby, keep="first", inplace=True)
    if df_left.empty:
        LOG.fatal("No rows in LEFT_CSV")
        sys.exit(1)
    if df_right.empty:
        LOG.fatal("No rows in RIGHT_CSV")
        sys.exit(1)
    if "diff" in df_left.columns:
        LOG.fatal("LEFT_CSV includes reserved column name 'diff'")
        sys.exit(1)
    if "diff" in df_right.columns:
        LOG.fatal("RIGHT_CSV includes reserved column name 'diff'")
        sys.exit(1)
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

    # Below, we read back the columns that got dropped in the earlier
    # groupby statements. This is only needed if '--cols' was specified:
    if cols is not None:
        dfs = []
        df_both = df_diff[df_diff["diff"] == "both"]
        df_left_only = df_diff[df_diff["diff"] == "left_only"]
        df_right_only = df_diff[df_diff["diff"] == "right_only"]
        dfs.append(df_left_only.merge(df_left, how="left", on=uids))
        dfs.append(df_right_only.merge(df_right, how="left", on=uids))
        df_both_left = df_both.merge(df_left, how="left", on=uids)
        common_cols = list(df_both_left.columns.intersection(df_right.columns))
        LOG.debug("common_cols: %s", common_cols)
        # For non-uid common columns where the values don't match, use the
        # value from 'left'
        dfs.append(df_both_left.merge(df_right, how="left", on=common_cols))
        df_diff = pd.concat(dfs).reset_index(drop=True)

    # Remove temporary columns we added above
    df_diff.drop(["count_left", "count_right", "_merge"], inplace=True, axis=1)
    # Make sure 'diff' column is the last column
    df_diff["diff"] = df_diff.pop("diff")
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
        LOG.info("Number of LEFT_ONLY rows: %s", df_left_only.shape[0])
    df_right_only = df_diff[df_diff["diff"] == "right_only"]
    if not df_right_only.empty:
        LOG.info("Number of RIGHT_ONLY rows: %s", df_right_only.shape[0])
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
    df_diff = _csv_diff(left_csv, right_csv, args.ignoredups, args.cols)
    _report_diff(df_diff)
    df_to_csv_file(df_diff, args.out)


################################################################################

if __name__ == "__main__":
    main()

################################################################################
