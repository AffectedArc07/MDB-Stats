#!/bin/bash

[ -d "./env" ] && echo "Existing env found. Removing..." && rm -rf ./env

echo "Setting up venv..."
python3 -m venv env
source env/bin/activate

echo "Installing dependencies..."
# Wheel gotta be done first because other requirements depend on it
python3 -m pip install wheel
# Now the rest of the requirements
python3 -m pip install -r requirements.txt
echo "Done"