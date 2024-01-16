<!--
    Copyright 2024 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# checksig.sh

checksig.sh checks signatures of Ghaf build packages and provenance files.

Checksig will automatically download required sha256tree script, server keys and
signature files if not already locally available.

It will store server keys and sha256tree.py script in "~/.ghafkeys" by default.
You can change the directory with `--keydir` option or by setting
CHECKSIG_KEYDIR environment variable.

Packages will be extracted to a temporary directory and if signature check is
successful package contents will be moved to `package_contents` directory
under current directory or under given directory when using `-C` option.

Moving of extracted files can be disabled with `--nosave` option, in that
case files extracted to temporary directory will be deleted. This may be useful
if you are just interested in checking the signature and don't need the files
at this point.

## Usage

```
Usage: ./checksig.sh [options] SIGNEDITEM

  SIGNEDITEM = Path or URL to item to check signature for

Options:
      --help, -h = Show this help
     --quiet, -q = Only show the signature check result
          -C DIR = Change directory before doing anything, create if not existing
 --keydir KEYDIR = Use alternate server key directory, create if not existing (default: ~/.ghafkeys)
                   (You can also set CHECKSIG_KEYDIR environment variable instead)
       --nocheck = Do not explicitly check for prerequisites
        --prereq = Just check the prerequisites
  --check-script = Run shellcheck and bashate on the script itself
         --clear = Remove server key directory and exit
    --sha256tree = Update sha256tree.py from repo even if it exists locally
        --nosave = Do not save extracted package content
              -- = Mark end of options (in case filename starts with a dash)
```
## Examples with outputs

Check that you have the required programs to run this script:

```
user@computer:~/ci-public/checksig$ ./checksig.sh --prereq
Command "python3" found.
Command "wget" found.
Command "tar" found.
Command "xxd" found.
Command "openssl" found.
Command "find" found.
Command "mktemp" found.
Command "realpath" found.
Command "chmod" found.
Command "grep" found.
Command "mv" found.
user@computer:~/ci-public/checksig$
```


Download package into "./verify" -directory and check it's signatures:

```
user@computer:~/ci-public/checksig$ ./checksig.sh -C ./verify https://vedenemo.dev/files/images/themisto/docs.x86_64-linux/8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc-themisto-94.tar.xz
Downloading https://vedenemo.dev/files/images/themisto/docs.x86_64-linux/8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc-themisto-94.tar.xz
/home/user/ci-public/checksig/ 100%[========================================================>]   3,67M  2,15MB/s    in 1,7s
Downloading sha256tree.py
Extracting /home/user/ci-public/checksig/verify/8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc-themisto-94.tar.xz to temp dir
Downloading key for themisto server
8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc: Signature check ok
Moving extracted files to /home/user/ci-public/checksig/verify/package_contents
user@computer:~/ci-public/checksig$
```

Check signature of a provenance file in current directory:

```
user@computer:~/ci-public/checksig/verify$ ../checksig.sh 6m6wyki67xqgvq8nzmarzdbqjsxx01yg-themisto-96-provenance.json
Downloading sha256tree.py
No signature file found, checking build report
vsjfm5wcgk66l8sz87afi2y46j0ywwm7-6m6wyki67xqgvq8nzmarzdbqjsxx01yg-themisto-96-provenance.json-themisto.signature found on build report, downloading
Downloading key for themisto server
6m6wyki67xqgvq8nzmarzdbqjsxx01yg-themisto-96-provenance.json: Signature check ok
user@computer:~/ci-public/checksig/verify$
```

Check signature of already downloaded package, don't save extracted files and
be quiet:

```
user@computer:~/ci-public/checksig/verify$ ../checksig.sh --nosave -q 8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc-themisto-94.tar.xz
8fw2y3462mm182dk360p356nv3nmhzi8-ghaf-doc: Signature check ok
user@computer:~/ci-public/checksig/verify$
```
