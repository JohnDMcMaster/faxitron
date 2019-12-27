For Faxitron DX-50 x-ray w/ DC5 option. Other systems may be supported in the future. Short term goal is to be able to control x-ray and decode images. Images are currently captured using Hamamatsu utility

For more information: https://nucwiki.org/wiki/index.php/Faxitron

sudo apt-get install -y python3-numpy python3-serial
sudo pip3 install libusb1

python3 xray.py --kvp 35 --time 300 --fire



Collect diagnostic information

python3 ham_info.py

Output will be in "dump"



Calibration

Ensure x-ray is off. Run:

python3 ham_raw.py  --exp 2000 -n 32 --postfix df_2000ms_x32

Turn on x-ray

Ex: python3 xray.py --kvp 35 --time 300 --fire --device /dev/ttyUSB0

While that is running...

Ensure nothing is in the chamber and the sensor is clean

python3 ham_raw.py  --exp 2000 -n 32 --postfix bf_35kvp_2000ms_x32

Then:

python3 cal.py out/2019-12-26_01_bf_35kvp_2000ms_x32/ out/2019-12-26_02_df_2000ms_x32/ cal

View results in "cal"

