#!/usr/bin/env bash

file=/etc/udev/rules.d/99-faxitron.rules
echo "Updating $file"

cat << EOF |sudo tee $file >/dev/null
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0661", ATTR{idProduct}=="a802", MODE="0666"
EOF

