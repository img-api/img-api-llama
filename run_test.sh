#!/bin/bash

cd "${BASH_SOURCE%/*}"

source .venv/bin/activate

#export PYTHONPATH=$PYTHONPATH:/home/amcell/LLAMA/llama-agentic-system

while true; do
    python3 llama_batch_process.py localhost 5000
    sleep 1s
    done

