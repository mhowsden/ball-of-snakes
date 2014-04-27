#!/bin/bash

source ../ve/bin/activate
export SETTINGS=/path/to/config
python iris.py

# this can be used for gunicorn
# gunicorn --access-logfile - -w 4 -b 127.0.0.1:5000 iris:app
