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


def show_help():
    """Show usage help and exit"""

    print(f"Usage: {sys.argv[0]} [options] [PATH1] [PATH2] ...")
    print()
    print("  PATHn = Paths to calculate sha256 hash for")
    print()
    print("Options:")
    print("             -- = Use to separate from paths possibly starting with '--'")
    print("        --plain = Just print the hash without entry type or basename")
    print("         --help = Show this usage help")
    print("        --debug = Enable printing of intermediate hashes to stderr")
    print("  --buffer=SIZE = Set buffer size to be used when calculating hash for files")
    print("                  (default: 1048576 bytes)")
    print("")
    sys.exit(0)


def sha256sum(path, buf_size, hashonly=False) -> str | None:
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
            sha = sha256sum(os.path.join(path, item), buf_size)
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
            while block := file.read(buf_size):
                hsh.update(block)

    # It's something else, ignore with warning
    else:
        print(
            f"Warning: Unknown type ({hex(fstat.st_mode)}): {path}", file=sys.stderr)
        return None

    if hashonly:
        res = hsh.hexdigest() + "\n"
    else:
        res = hsh.hexdigest() + f" {ptype} " + os.path.basename(path) + "\n"

    if DEBUG:
        print(res, end="", file=sys.stderr)
    return res


def main(args: list[str]):
    """Process options and then call sha256sum for rest of arguments"""

    plain = False
    bufsiz = 1024*1024
    args.pop(0)

    while args and args[0].startswith("--"):
        if args[0] == "--":
            args.pop(0)
            break
        if args[0] == "--plain":
            plain = True
        elif args[0] == "--help":
            show_help()
        elif args[0] == "--debug":
            global DEBUG  # pylint: disable=global-statement
            DEBUG = True
        elif args[0].startswith("--buffer="):
            args[0] = args[0].removeprefix("--buffer=")
            bufsiz = int(args[0])
            if bufsiz <= 0:
                print(f"Invalid buffer size: {bufsiz}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Invalid argument: {args[0]}", file=sys.stderr)
            sys.exit(1)

        args.pop(0)

    for arg in args:
        print(sha256sum(arg, bufsiz, hashonly=plain), end="")


# ------------------------------------------------------------------------
# If this was invoked directly from command line, run main function
# ------------------------------------------------------------------------
if __name__ == "__main__":
    main(sys.argv[:])
