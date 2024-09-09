#!/bin/bash

cd "${BASH_SOURCE%/*}"

if [ ! -d ".venv" ]
then
   echo "INSTALLING VENV "
   python3 -m venv .venv
fi

echo "UPDATING IMG-API"

. .venv/bin/activate

git pull --rebase
pip3 install -r requirements.txt --upgrade
