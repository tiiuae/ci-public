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
            buildInputs = [pkgs.reuse];
          } ''
            cd ${../.}
            reuse --root . lint
            touch $out
          '';
      }
      //
      # merge in the package derivations to force a build of all packages during a `nix flake check`
      (with lib; mapAttrs' (n: nameValuePair "package-${n}") self'.packages);
  };
}
