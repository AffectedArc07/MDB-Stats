#!/bin/bash

[ ! -d "./env" ] && echo "Environment not found. Run install.sh first." && exit

source env/bin/activate
python3 main.py