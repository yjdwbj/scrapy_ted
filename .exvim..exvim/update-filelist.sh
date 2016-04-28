#!/bin/bash
export DEST="./.exvim..exvim"
export TOOLS="/root/.vim/tools/"
export IS_EXCLUDE=
export FOLDERS=""
export FILE_SUFFIXS=".pyc"
export TMP="${DEST}/_files"
export TARGET="${DEST}/files"
export ID_TARGET="${DEST}/idutils-files"
sh ${TOOLS}/shell/bash/update-filelist.sh
