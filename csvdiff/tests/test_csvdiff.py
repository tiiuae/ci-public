#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2022-2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=invalid-name, global-statement, redefined-outer-name

""" Tests for csvdiff """

import os
import subprocess
import shutil
from pathlib import Path
import pytest

MYDIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_WORK_DIR = None
REPOROOT = MYDIR / ".."
CSVDIFF = MYDIR / ".." / "src" / "csvdiff.py"

################################################################################


@pytest.fixture(scope="session")
def test_work_dir(tmp_path_factory):
    """Fixture for session-scope tempdir"""
    tempdir = tmp_path_factory.mktemp("test_csvdiff")
    return Path(tempdir)


@pytest.fixture(autouse=True)
def set_up_test_data(test_work_dir):
    """Fixture to set up the test data"""
    print("setup")
    global TEST_WORK_DIR
    TEST_WORK_DIR = test_work_dir
    TEST_WORK_DIR.mkdir(parents=True, exist_ok=True)
    print(f"using TEST_WORK_DIR: {TEST_WORK_DIR}")
    os.chdir(TEST_WORK_DIR)
    yield "resource"
    print("clean up")
    shutil.rmtree(TEST_WORK_DIR)


################################################################################


def test_nix_shell():
    """Test nix-shell doesn't fail and enters venv"""
    # Test running nix-shell. Inside the shell, test that
    # VIRTUAL_ENV variable is set, exit with failure if it is not set:
    run_cmd = "if [ -z ${VIRTUAL_ENV+x} ]; then exit 1; else exit 0; fi"
    cmd = ["nix-shell", "--run", run_cmd]
    os.chdir(REPOROOT)
    assert subprocess.run(cmd, check=True).returncode == 0
    os.chdir(TEST_WORK_DIR)


################################################################################


def test_csvdiff_help():
    """Test csvdiff command line argument: '-h'"""
    cmd = [CSVDIFF, "-h"]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_csvdiff_match():
    """Test csvdiff with matching files"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    cmd = [CSVDIFF, left_path, left_path]
    assert subprocess.run(cmd, check=True).returncode == 0


def test_csvdiff_nomatch():
    """Test csvdiff with csv input files that should output a diff"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    right_path = MYDIR / "resources" / "right.csv"
    assert right_path.exists()
    out_path = TEST_WORK_DIR / "diff.csv"
    cmd = [CSVDIFF, "--out", out_path, left_path, right_path]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 1
    assert out_path.exists()
    assert "LEFT_ONLY rows: 1" in ret.stderr
    assert "RIGHT_ONLY rows: 1" in ret.stderr


def test_csvdiff_ignoredups():
    """Test csvdiff ignoredups"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    left_dups_path = MYDIR / "resources" / "left_dups.csv"
    assert left_dups_path.exists()
    # Without --ignoredups, the following reports a diff:
    cmd = [CSVDIFF, left_path, left_dups_path]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(ret)
    assert ret.returncode == 1
    assert "RIGHT_ONLY rows: 1" in ret.stderr
    # With --ignoredups, the following reports a no diffs:
    cmd = [CSVDIFF, "--ignoredups", left_path, left_dups_path]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 0


def test_csvdiff_cols_valid():
    """Test csvdiff with --cols with valid column names"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    cmd = [CSVDIFF, left_path, left_path, "--cols=vuln_id,package"]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 0


def test_csvdiff_cols_invalid():
    """Test csvdiff with --cols with invalid column names"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    cmd = [CSVDIFF, left_path, left_path, "--cols=a"]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 1


def test_csvdiff_cols_mismatch():
    """Test csvdiff with mismatching columns"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    right_path = MYDIR / "resources" / "cols_mismatch.csv"
    assert right_path.exists()
    cmd = [CSVDIFF, left_path, right_path]
    assert subprocess.run(cmd, check=False).returncode == 1


def test_csvdiff_cols_dups():
    """Test csvdiff combining both --cols and --ignoredups"""
    left_path = MYDIR / "resources" / "left_cols_dups.csv"
    assert left_path.exists()
    right_path = MYDIR / "resources" / "right_cols_dups.csv"
    assert right_path.exists()
    # Without --cols and --ignoredups
    cmd = [CSVDIFF, left_path, right_path]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 1
    assert "LEFT_ONLY rows: 3" in ret.stderr
    assert "RIGHT_ONLY rows: 1" in ret.stderr
    # With --cols and without --ignoredups
    cmd = [CSVDIFF, left_path, right_path, "--cols=vuln_id,package"]
    ret = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert ret.returncode == 1
    assert "LEFT_ONLY rows: 3" in ret.stderr
    # With --cols and --ignoredups
    cmd = [
        CSVDIFF,
        left_path,
        right_path,
        "--ignoredups",
        "--cols=vuln_id,package",
    ]
    assert subprocess.run(cmd, check=False).returncode == 0


def test_csvdiff_noentries():
    """Test csvdiff with no rows in one of the csv input files"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    right_path = MYDIR / "resources" / "noentries.csv"
    assert right_path.exists()
    cmd = [CSVDIFF, left_path, right_path]
    assert subprocess.run(cmd, check=False).returncode == 1


def test_csvdiff_empty():
    """Test csvdiff with an empty csv file"""
    left_path = MYDIR / "resources" / "left.csv"
    assert left_path.exists()
    right_path = MYDIR / "resources" / "empty.csv"
    assert right_path.exists()
    cmd = [CSVDIFF, left_path, right_path]
    assert subprocess.run(cmd, check=False).returncode == 1


################################################################################


if __name__ == "__main__":
    pytest.main([__file__])


################################################################################
