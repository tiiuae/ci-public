<!--
    Copyright 2022-2023 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# csvdiff

`csvdiff` is a command line tool that compares two csv files and reports the comparison summary in stderr and the writes the comparison details to a file.


## Running from Nix Development Shell

If you have nix flakes enabled, run:
```bash
$ git clone https://github.com/tiiuae/ci-public/
$ cd ci-public/csvdiff
$ nix develop
```

You can also use `nix-shell` to enter the development shell:
```bash
$ git clone https://github.com/tiiuae/ci-public/
$ cd ci-public/csvdiff
$ nix-shell
```

From the development shell, you can run `csvdiff` as follows:
```bash
$ csvdiff --help
```

## Running as Nix Flake
`csvdiff` can be run as a [Nix flake](https://nixos.wiki/wiki/Flakes) from the `tiiuae/ci-public` repository:
```bash
# '--' signifies the end of argument list for `nix`.
# '--help' is the first argument to `csvdiff`
$ nix run github:tiiuae/ci-public?dir=csvdiff#csvdiff -- --help
```

or from a local repository:
```bash
$ git clone https://github.com/tiiuae/ci-public
$ cd ci-public/csvdiff
$ nix run .#csvdiff -- --help
```

## Example Usage
Below example compares [left.csv](./tests/resources/left.csv) and [right.csv](./tests/resources/right.csv) example targets:

```bash
$ csvdiff tests/resources/left.csv tests/resources/right.csv 
INFO     Comparing 'LEFT_CSV=tests/resources/left.csv' 'RIGHT_CSV=tests/resources/right.csv'
INFO     Number of common rows: 5
WARNING  Number of LEFT_ONLY rows: 1
WARNING  Number of RIGHT_ONLY rows: 1
INFO     Wrote: csvdiff.csv
```
