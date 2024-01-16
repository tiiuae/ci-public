<!--
    Copyright 2024 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# ci-public

CI/CD related files

## Directories

| Directory | Description
| --- | ---
| addtimestamp | Tool for adding timestamp to build report .json
| containers | Everything related to dockerized server solution
| csvdiff | Tool for comparing .csv files
| docs | Documentation
| githooks | Git hook scripts
| hydractl | Tool for creating Hydra projects and jobsets
| hydrascrape | Tool for scraping build info from Hydra web UI
| indexer | Tool for creating index files for build reports
| Jenkisfiles | Jenkins post processing scripts
| LICENSES | Licenses used in this repository
| yubihsm | Yubihsm container stuff
| sha256tree | [Checksum calculator for directory trees](./sha256tree/sha256tree.md)
| checksig | [Signature checker script](./checksig/checksig.md)

## Git commit hook

When contributing to this repo you should take the git commit hook into use.

This hook will check the commit message for most trivial mistakes against [current Ghaf commit message guidelines](https://github.com/tiiuae/ghaf/blob/main/CONTRIBUTING.md#commit-message-guidelines)

### Installing git hooks

Just run ``./githooks/install-git-hooks.sh`` in repository main directory, and you should be good to go. Commit message checking script will then run when you commit something.

If you have branches before the git hooks were committed to the repo, you'll have to either rebase them on top of main branch or cherry pick the git hooks commit into your branch.

Also note that any existing commit messages in any branch won't be checked, only new commit messages will be checked.

If you encounter any issues with the git commit message hook, please report them. And while waiting for a fix, you may remove the hook by running ``rm -f .git/hooks/commit-msg`` in the main directory of the repository.

## Guidelines for Bash scripts

If you are writing bash scripts for this project, please follow these [guidelines](./docs/bash_script_style_guide.md).

## Licensing

This repository follows the Ghaf team licensing:

| License Full Name | SPDX Short Identifier | Description
| --- | --- | ---
| Apache License 2.0 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Source code
| Creative Commons Attribution Share Alike 4.0 International | [CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html) | Documentation

See [LICENSE.Apache-2.0](./LICENSES/LICENSE.Apache-2.0) and [LICENSE.CC-BY-SA-4.0](./LICENSES/LICENSE.CC-BY-SA-4.0) for the full license text.
