#!/usr/bin/env bash
set -ex

n=${CALN,32}
d=$(python3 cal_dir.py)
echo "Output dir $d: writing $n files"
mkdir -p $d
python3 main.py --kvp 0 -n $n --dir $d/df --raw
python3 main.py --kvp 35 -n $n --dir $d/ff --raw
python3 cal.py $d/ff $d/df $d

