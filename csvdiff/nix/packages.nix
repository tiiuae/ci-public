# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
_: {
  perSystem = {
    pkgs,
    lib,
    ...
  }: let
    pp = pkgs.python3Packages;
  in {
    packages = rec {
      default = csvdiff;

      csvdiff = pp.buildPythonPackage {
        pname = "csvdiff";
        version = pkgs.lib.removeSuffix "\n" (builtins.readFile ../VERSION);
        format = "setuptools";

        src = lib.cleanSource ../.;

        pythonImportsCheck = ["csvdiff"];

        propagatedBuildInputs =
          [
            pkgs.reuse
          ]
          ++ (with pp; [
            colorlog
            gitpython
            pandas
            tabulate
          ]);
      };
    };
  };
}
