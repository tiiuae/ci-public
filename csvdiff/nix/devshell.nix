# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{
  perSystem = {pkgs, ...}: {
    devShells.default = pkgs.mkShell rec {
      name = "csvdiff-dev-shell";

      packages = with pkgs; [
        python3.pkgs.black
        python3.pkgs.colorlog
        python3.pkgs.deploykit
        python3.pkgs.invoke
        python3.pkgs.numpy
        python3.pkgs.pandas
        python3.pkgs.pycodestyle
        python3.pkgs.pylint
        python3.pkgs.pytest
        python3.pkgs.tabulate
        python3.pkgs.venvShellHook
        reuse
      ];

      venvDir = "venv";
      postShellHook = ''
        export PYTHONPATH="$PYTHONPATH:$(pwd)"

        # https://github.com/NixOS/nix/issues/1009:
        export TMPDIR="/tmp"

        # Enter python development environment
        make install-dev
      '';
    };
  };
}
