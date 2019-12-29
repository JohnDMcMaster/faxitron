#!/usr/bin/env bash

file=/etc/udev/rules.d/99-faxitron.rules
echo "Updating $file"

cat << EOF |sudo tee $file >/dev/null
# C9730DK-11 (DC5)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0661", ATTR{idProduct}=="a802", MODE="0666"
# DC12
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0661", ATTR{idProduct}=="a800", MODE="0666"
EOF

