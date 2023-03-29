# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python3Packages,
}:

pkgs.mkShell {
  name = "csvdiff-dev-shell";

  buildInputs = [ 
    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.colorlog
    pythonPackages.wheel
    pythonPackages.pycodestyle
    pythonPackages.pylint
    pythonPackages.black
    pythonPackages.pytest
    pythonPackages.venvShellHook
  ];
  venvDir = "venv";
  postShellHook = ''
    # https://github.com/NixOS/nix/issues/1009:
    export TMPDIR="/tmp"
    
    # Enter python development environment
    make install-dev
  '';
}
