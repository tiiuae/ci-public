#!/bin/sh

# give build id as argument and it will be unhandled

set -x
sed -i '/^'"$1"'$/d' handled_builds
[ ! -e $1.json ] || rm $1.json
