#!/bin/bash

tmux new-session -d -s my_server '/home/amcell/LLAMA/img-api-llama/run_test.sh'
tmux split-window -h -t my_server '/home/amcell/LLAMA/img-api-llama/run_test.sh'
tmux split-window -hf -t my_server '/home/amcell/LLAMA/img-api-llama/run.sh'
