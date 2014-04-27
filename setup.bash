#!/bin/bash

/usr/bin/virtualenv ve
source ve/bin/activate
pip install -U pip
pip install -r requirements.txt
