# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python3Packages,
}:

pythonPackages.buildPythonPackage rec {
  pname = "csvdiff";
  version = pkgs.lib.removeSuffix "\n" (builtins.readFile ./VERSION);
  format = "setuptools";

  src = ./.;

  propagatedBuildInputs = [ 
    pythonPackages.pandas
    pythonPackages.colorlog
    pythonPackages.wheel
  ];
}