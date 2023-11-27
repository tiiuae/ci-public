# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{
  perSystem = {pkgs, ...}: {
    devShells.default = pkgs.mkShell rec {
      name = "csvdiff-dev-shell";

      packages = with pkgs; [
        reuse
        (
          pkgs.python3.withPackages (ps:
            with ps; [
              colorlog
              deploykit
              invoke
              numpy
              pandas
              pytest
              tabulate
            ])
        )
      ];
      shellHook = ''
        export PYTHONPATH="$PYTHONPATH:$(pwd)"
      '';
    };
  };
}
