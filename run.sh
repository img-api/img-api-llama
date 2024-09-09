#!/bin/bash

cd "${BASH_SOURCE%/*}"

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

. .venv/bin/activate

echo "Running flask!"
export FLASK_DEBUG=1
export FLASK_APP=imgapi_llama_launcher.py
export FLASK_PORT=5111

pip3 install yfinance --upgrade

while true; do
    echo " "
    echo "------------------------------"
    echo "------------ LAUNCH ----------"
    echo "------------------------------"
    echo " "

    flask run --host=0.0.0.0 -p $FLASK_PORT --with-threads
    sleep 10s
done

$SHELL