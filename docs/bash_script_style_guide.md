<!--
    Copyright 2022-2023 TII (SSRC) and the Ghaf contributors
    SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Bash Script Style Guide

General guidelines for bash scripts. (May be applied to any shell scripts on compatible parts.)

1. Use 4 spaces indentation. Spare tabs for Makefiles.
2. Remove whitespaces from the ends of the lines.
3. Quote variables: `"$VAR"`. Even in cases where it is not absolutely necessary. Comment cases where quotes explicitly can not be used. Disable shellcheck complaint about unquoted variable like in this example:
    ```
    # shellcheck disable=SC2086 # $SIGN_SSHOPTS is purposefully unquoted here, it contains several space separated options for ssh
    if ssh -n -o BatchMode=yes $SIGN_SSHOPTS "$SIGNING_SRV" "${SIGNING_SRV_PATH}/start.sh" sign "-h=$SHA256SUM" > "$SIGNATURE_FILE"; then
    ...
    ```
4. Use curly braces whenever you are concatenating something after a variable: `"${IMGBUILD}/output"`.
5. Use `[ ]` and `[[ ]]` instead of `test`.
6. Use `case` instead of `if - elif` structure if possible.
7. Put space after hash sign in comments: `# Comment`.
8. Indent comments the same amount as the line being commented.
9.  Do not add **x** to string comparisons: `[ “x$VAR” = “xBlah” ]`. It is redundant in modern Bash.
10. To check if variable is empty or unset, use: `[ -z “$VAR” ]`.
11. To check that the variable is set to something else than an empty string, use: `[ -n “$VAR” ]`.
12. To invert, place inversion inside brackets: `[ ! -e “$FILE” ]`.
13. Output error and warning messages to stderr instead of stdout: `echo Error Message >&2`.
14. Use `$(command)` instead of `` `command` `` when capturing command output.
15. Put “then” on the same line with “if”, put "do" on the same line with "while", apply rule for rest of similar structures:
    ```
    if [ -n “$VAR” ]; then
        # Do stuff
    fi

    while [ -z "$STR" ]; do
        # Do other stuff
    done
    ```
16. Indent cases like this:
    ```
    case "$1" in
    opt1)
        # Option 1
        do_stuff here
    ;;
    opt2|opt3)
        # Option 2 or 3
        do_other stuff
    ;;
    *)
        # Default
        do_default stuff
    ;;
    esac
    ```
17. Place generic case `*)` last in the case.
18. An empty generic case is not required but is allowed for clarity.
19. Commenting on empty cases is recommended but not required.
20. Use local variables in a function, if the values are not needed outside the function.
21. Declare local variables separately from assigning a value (at the start of a function if feasible). Only if the value assigned is a simple constant, you can declare and assign at the same time.
    ```
    function Not_ok_func {
        local a="$(Other_func)"   # Not ok

        if [ $? -eq 0 ]; then
            # This part would be run, even if 'Other_func' fails
            # and even if stop on any error is set
            # '$?' would contain status of 'local' command not 'Other_func'
            ...
        fi
    }

    function Ok_func {
        local a=1                 # Ok

        local b="constant string" # Ok

        local c
        c="$(Other_func)"         # Ok

        ...
    }
    ```
22. Use all lowercase letters in local variable names and all uppercase letters in global variables.
23. Start function names with the capital letter and keep the rest lowercase. This way they stand out from shell commands and executables, which are usually all lowercase.
24. Use comments whenever it adds the understanding of what the script does, but try not to comment on every single line.
25. Always comment on regular expressions and sed magic. E.g. what are you searching for and what do you want to replace it with.
26. Avoid here documents, if possible. These may break indentation and make the script harder to follow.
    For example, if you are generating a text file, a series of echos indent nicely and accomplish the same as cat with here document input. If avoiding the use of a here document would require using a temporary file, then the use of a here document is acceptable.
27. Avoid using ‘sudo’ if it is in any way possible for the task you are trying to do. Using ‘sudo’ for example dd:ing a disk image onto physical disk is acceptable, but ‘sudo’ is not absolutely necessary for creating a disk image file.
28. Do not expect the user to run the script as root as a way to avoid sudo inside the script, as that will cause everything in the script to be done as root, instead of just absolutely necessary parts.
29. Exceptions are allowed for a good reason. Add the reason to a comment as well.
30. Some third-party scripts do not follow this style. If editing such a script, try to follow the original script style. Of course, you may change the whole script to this style, but in that case, please keep the style change in its own commit, so that functional changes are not hidden between several style changes.
31. Use `shellcheck` and `bashate -i E006` (Ignore long lines) to check your scripts before pushing. There should be no complaints at all. If you are sure, your code is correct, but shellcheck complains about it, add a `# shellcheck disable=SCxxx` comment to disable the specific complaint, also explain the reason for the exception in the comment.

If you're using VSCode for your bash scripting, using the shellcheck extension is highly recommended. With it, you get suggestions to format your code already when editing it.

These guidelines are naturally debatable, so any improvement suggestions are welcome.

If you would like to contribute, please consider opening a pull request. In case of any bugs or errors in the content, feel free to create an [issue](https://github.com/tiiuae/ci-public/issues). You can also [create an issue from code](https://docs.github.com/en/issues/tracking-your-work-with-issues/creating-an-issue#creating-an-issue-from-code).
