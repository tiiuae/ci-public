<!--
    Copyright 2022-2023 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# sha256tree

Calculates checksum for files, directories and various other objects that may be found on filesystems.

Primary use is to be able to calculate single hash for build output directory so it can be signed.

## Usage
```
Usage: python3 sha256tree.py [options] [PATH1] [PATH2] ...

  PATHn = Paths to calculate sha256 hash for

Options:
             -- = Use to separate options from paths possibly starting with '--'
        --plain = Just print the hash without entry type or basename
         --help = Show this usage help
        --debug = Enable printing of intermediate hashes to stderr
  --buffer=SIZE = Set buffer size to be used when calculating hash for files
                  (default: 1048576 bytes)
```

## Example outputs
```
user@computer:~/ci-public/sha256tree$ python3 sha256tree.py ~/Documents
8dcc42048b55d5b12ef68fd82f0599d1234ae7ae8c78c6434d4a4e360c6b4a11 d Documents
user@computer:~/ci-public/sha256tree$

user@computer:~/ci-public/sha256tree$ python3 sha256tree.py --plain -- ~/Documents
8dcc42048b55d5b12ef68fd82f0599d1234ae7ae8c78c6434d4a4e360c6b4a11
user@computer:~/ci-public/sha256tree$

user@computer:~/ci-public/sha256tree$ python3 sha256tree.py ~/ci-public/*
c9ad29bd0698d5698c0338f998f44435c9e7c35745c7261647ff77dd829eb072 d addtimestamp
3ac612b158943af3f963fa452234f62e227e4144ec02e4193b6fd168334e9666 d autodeployment
1dc08920cff721b83861c8464b392412c2ea2aa976ca35b02d9f8c9d8922e50f d containers
10603ed798c4525dcf86caeb27ea8c6e02bcf8cd2bd8136b4d072807b0dc1e6c d csvdiff
69e2a1549b3007f956241756cb046ba02f07687c405629ff6092da2bb9f388e7 d docs
c815bf696a5ca6e012731943f44f6c3606eeaf5969fa041618ddb7dac891bbda d githooks
e0b02da9d20d8e187dfc9dc09d5c4a9f42dbb338d933cb1e6c904800421dc786 d hydractl
79bf0b6ebf6b73e256e4a1fdd9fb6d352312d0b9536aaa55ebb8d55a71dfcd2a d hydrascrape
dcd57ec870e3845d102d2b83e63b26330eedb531cca3e78d53e32676706f5282 d indexer
b9b25a20cbfc7df0d296e1acca2b995180791240ced37df1b225ca7e44448662 d jenkins
f5438ae807a65da784c792d6278bdf61ba1fa238e89d326459392ba1085ffb03 d Jenkinsfiles
650c2fc6441df70aff0ad1c234fc99d48b06dc0235eeec7145bfa77262db4624 d LICENSES
0305ca6ef74c1919a8d3d70cd43f46fbb309aeaf4aca1ad2de895909c7266b1d d pullrequests
a2627e2687112e6ddf383c35f5a83dde6d2cfdc487a53a7ccaa5f9df9366155a - README.md
9aef0d351ab6a3780d6069c8a081022c91818523182d4662c6b143224e12a112 d sha256tree
859ad16cff64aea103b3e64ad5ebb237e8b516cef613319c32f87d2374c45051 d slsa
bbf26fe3839f81549f6c759608eb6db58ead67ddd340f23c7abb978c48a34842 d yubihsm
user@computer:~/ci-public/sha256tree$
```
## How different filesystem items are handled

Type | Handling | Notes
---|---|---
File | Calculate hash of the contents | Hash is the same as with sha256sum
Directory | Recusively hash everything in the directory | Hash is calculated from the hash listing of directory contents
Symbolic link | Calculate hash of the link target string (not the target content) | Allows calculating hash for non existing targets also
Block/Char device | Calculate hash for device major and minor numbers (not the device content) | Allows calculating has for special device files, without touching any device
Named pipe/socket | Calculate hash from the entry filename

Type of the item will change the hash for the containing directory. So e.g. a subdirectory cannot be converted to a file entry without changing the hash.

## File permissions, ownership and dates

Permissions, ownership and the file creation and access dates do not affect the calculated hash in any way.

## Justification

### Why not just use ```sha256sum```?
sha256sum cannot calculate checksum for a directory tree.

### There's ```sha256deep``` that can calculate checksum for directory trees also, why not use that?
sha256deep would try to follow symbolic links and calculate checksums for linked directory tree instead of the link iself.
Build outputs could potentially also contain symbolic links that point to non-existing destinations.

sha256deep would also try to calculate checksum for e.g. block device contents, instead of the device special file itself.
Build outputs could potentially also contain special device files and such.
