# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0
{
  description = "Flakes file for csvdiff";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixos-unstable;

  outputs = { self, nixpkgs }:
    let
      pkgs = import nixpkgs { system = "x86_64-linux"; };
      csvdiff = import ./default.nix { pkgs = pkgs; };
      csvdiff-shell = import ./shell.nix { pkgs = pkgs; };
    in rec {
      
      # nix package
      packages.x86_64-linux = {
        inherit csvdiff;
        default = csvdiff;
      };

      # nix run .#csvdiff
      apps.x86_64-linux.csvdiff = {
        type = "app";
        program = "${self.packages.x86_64-linux.csvdiff}/bin/csvdiff";
      };

      # nix develop
      devShells.x86_64-linux.default = csvdiff-shell;
    };
}
