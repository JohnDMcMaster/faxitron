#!/usr/bin/env bash

mkdir -p cal
python3 ham_raw.py --kvp 0 -n 32 --dir cal/df
python3 ham_raw.py --kvp 0 -n 32 --dir cal/ff
python3 cal.py cal/ff cal/df cal

