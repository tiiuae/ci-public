# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{lib, ...}: {
  perSystem = {
    self',
    pkgs,
    ...
  }: {
    checks =
      {
        # checks that copyright headers are compliant
        reuse =
          pkgs.runCommandLocal "reuse-lint" {
            nativeBuildInputs = [pkgs.reuse];
          } ''
            cd ${../.}
            reuse --root . lint
            touch $out
          '';
        # pycodestyle
        pycodestyle =
          pkgs.runCommandLocal "pycodestyle" {
            nativeBuildInputs = [pkgs.python3.pkgs.pycodestyle];
          } ''
            cd ${../.}
            pycodestyle --max-line-length 90 $(find . -name "*.py" ! -path "*venv*" ! -path "*eggs*")
            touch $out
          '';
        # pylint
        pylint =
          pkgs.runCommandLocal "pylint" {
            nativeBuildInputs = with pkgs.python3Packages; [colorlog pandas pylint pytest setuptools];
          } ''
            cd ${../.}
            pylint --enable=useless-suppression --fail-on=I0021 --disable=duplicate-code -rn $(find . -name "*.py" ! -path "*venv*" ! -path "*eggs*")
            touch $out
          '';
      }
      //
      # merge in the package derivations to force a build of all packages during a `nix flake check`
      (with lib; mapAttrs' (n: nameValuePair "package-${n}") self'.packages);
  };
}
