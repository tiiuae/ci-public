# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2022 Tero Tervala <tero.tervala@unikie.com>
# SPDX-FileCopyrightText: 2022 Unikie

import re


def munge(m):
    try:
        val = float(m.group(2))
    except ValueError:
        return m.group(0)

    if (val <= 5.0):
        val /= 5.0
        r = int(val * 255.0)
        g = 255
    else:
        val -= 5.0
        val /= 5.0
        r = 255
        g = 255 - int(val * 255.0)

    c = r << 16 | g << 8
    return m.group(1) + f'<SPAN style="color: #{c:06X}">' + m.group(2) + "</SPAN>"


def colorify(value):
    # Color severity values
    value = re.sub(r"(\s)(\d\d?\.\d$)", munge, value, flags = re.MULTILINE | re.UNICODE)
    # Color success/failure
    value = re.sub(r"(FAILURE)", r'<SPAN style="color: #ff0000">\1</SPAN>', value, flags = re.MULTILINE | re.UNICODE)
    value = re.sub(r"(SUCCESS)", r'<SPAN style="color: #00ff00">\1</SPAN>', value, flags = re.MULTILINE | re.UNICODE)
    return value


def linkify(value):
    # Replace url with a link
    regex = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE | re.UNICODE)
    return regex.sub(r'<A href="\1">\1</A>', value)


def webify(text):

    text = colorify(text)
    text = linkify(text)

    return text
