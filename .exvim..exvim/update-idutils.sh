#!/bin/bash
export DEST="./.exvim..exvim"
export TOOLS="/root/.vim/tools/"
export TMP="${DEST}/_ID"
export TARGET="${DEST}/ID"
sh ${TOOLS}/shell/bash/update-idutils.sh
