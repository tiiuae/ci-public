# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
# SPDX-License-Identifier: Apache-2.0

"""Calculate a sha256 checksum for file (symlink,device,fifo,socket) or directory"""


import hashlib
import sys
import os
import stat

# Setting DEBUG to True will print all intermediate hashes to stderr
DEBUG = False
# Encoding for strings to be hashed
ENCOD = 'UTF-8'
# Buffer size to use when calculating file hashes
BUFSIZ = 1024*1024


def sha256sum(path) -> str | None:
    """CalculateS a sha256 checksum for a given path"""

    ptype = '-'
    hsh = hashlib.sha256()

    fstat = os.lstat(path)

    # It's a symbolic link, hash target path
    if stat.S_ISLNK(fstat.st_mode):
        hsh.update(os.readlink(path).encode(ENCOD))
        ptype = 'l'

    # It's a directory, hash every item in directory and hash the sha256sum output
    elif stat.S_ISDIR(fstat.st_mode):
        dlist: list = os.listdir(path)
        dlist.sort()
        for item in dlist:
            sha = sha256sum(os.path.join(path, item))
            if sha is not None:
                hsh.update(sha.encode(ENCOD))
        ptype = 'd'

    # It's a block device, hash major and minor numbers
    elif stat.S_ISBLK(fstat.st_mode):
        major = os.major(fstat.st_rdev)
        minor = os.minor(fstat.st_rdev)
        hsh.update(f"{major} {minor}".encode(ENCOD))
        ptype = 'b'

    # It's a character device, hash major and minor numbers
    elif stat.S_ISCHR(fstat.st_mode):
        major = os.major(fstat.st_rdev)
        minor = os.minor(fstat.st_rdev)
        hsh.update(f"{major} {minor}".encode(ENCOD))
        ptype = 'c'

    # It's a named pipe, just hash the name
    elif stat.S_ISFIFO(fstat.st_mode):
        hsh.update(str(os.path.basename(path)).encode(ENCOD))
        ptype = 'p'

    # It's a socket, just hash the name
    elif stat.S_ISSOCK(fstat.st_mode):
        hsh.update(str(os.path.basename(path)).encode(ENCOD))
        ptype = 's'

    # It's a regular file, hash the contents
    elif stat.S_ISREG(fstat.st_mode):
        with open(path, "rb") as file:
            while block := file.read(BUFSIZ):
                hsh.update(block)

    # It's something else, ignore with warning
    else:
        print(
            f"Warning: Unknown type ({hex(fstat.st_mode)}): {path}", file=sys.stderr)
        return None

    res = hsh.hexdigest() + f" {ptype} " + os.path.basename(path) + "\n"
    if DEBUG:
        print(res, end="", file=sys.stderr)
    return res


# ------------------------------------------------------------------------
# If this was invoked directly from command line, run sha256sum for each arg
# ------------------------------------------------------------------------
if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(sha256sum(arg), end="")
