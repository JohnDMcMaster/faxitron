#!/usr/bin/env bash
set -ex

# Some units (ex: MX-20) don't have serial port readily availible
manual=${MANUAL:-false}
# 16 is usually good enough, 32 is a little better
n=${CALN:-16}
d=$(python3 cal_dir.py)
echo "Output dir $d: writing $n files"
mkdir -p $d
python3 main.py --kvp 0 -n "$n" --dir "$d/df" --raw

if ${manual}; then
    echo "Turn x-ray on"
    read -p "Press enter to continue"
    python3 main.py --kvp 0 -n "$n" --dir "$d/ff" --raw
else
    python3 main.py --kvp 35 -n "$n" --dir "$d/ff" --raw
fi

python3 cal.py $d/ff $d/df $d

