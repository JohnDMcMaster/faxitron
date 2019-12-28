#!/usr/bin/env bash
set -ex

n=32
mkdir -p cal
python3 main.py --kvp 0 -n $n --dir cal/df --raw
python3 main.py --kvp 35 -n $n --dir cal/ff --raw
python3 cal.py cal/ff cal/df cal

