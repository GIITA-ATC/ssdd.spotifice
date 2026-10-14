#!/bin/bash

cd "$(dirname "$0")" || exit 1

# Only activate the virtual environment if it exists
ACTIVATE=""
[ -f .venv/bin/activate ] && ACTIVATE="source .venv/bin/activate && "

tmux new-session -d -s session

tmux set-option -g mouse on
tmux setw -g monitor-activity on
tmux set-option -g visual-activity on
tmux bind-key x kill-session
tmux set-option -g set-titles off

tmux split-window -t session:0 -h
tmux split-window -t session:0 -v
tmux send-keys -t session:0.0 "${ACTIVATE}python3 media_provider.py --Ice.Config=provider.config" C-m
tmux send-keys -t session:0.1 "${ACTIVATE}python3 media_render.py --Ice.Config=render.config" C-m
tmux send-keys -t session:0.2 "${ACTIVATE}python3 media_control.py --Ice.Config=control.config" C-m
tmux attach-session -t session
