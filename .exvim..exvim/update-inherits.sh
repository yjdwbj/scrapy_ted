#!/bin/bash
export DEST="./.exvim..exvim"
export TOOLS="/root/.vim/tools/"
export TMP="${DEST}/_inherits"
export TARGET="${DEST}/inherits"
sh ${TOOLS}/shell/bash/update-inherits.sh
