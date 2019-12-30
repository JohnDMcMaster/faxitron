# Faxitron Python Library

For Faxitron DX-50 x-ray w/ DC5 option. Other systems may be supported in the future. Short term goal is to be able to control x-ray and decode images. Images are currently captured using Hamamatsu utility

Specifically, a "DC5" is a "HAMAMATSU C9730DK-11". Mine is version 1.21, but a C9730DK-11 version 1.18 was briefly tested and works, pending a fix being verified.

For more information: https://nucwiki.org/wiki/index.php/Faxitron

Features:
* Command line image capture
* Cross platform
* Calibration routine w/ scaling and bad pixel replace
* Histogram equalization
* Combines multiple images to improve quality
* Detects door state

Workhorse utilities:
* main.py: fire x-ray and capture images
* cal.py: create bad pixel map

Other utilities:
* decode_dcam.py: convert Hamamatsu DCAMIMG (".img") to .png
* dump.py: collect diagnostic info such as hardware versions
* ham_process.py: process an already captured image sequence into corrected .png
* ham_raw.py: direct sensor control. Doesn't know about x-ray
* usbrply.py: convert Wireshark USB .cap file into Python code
* xray.py: direct x-ray control. Doesn't know about sensor

DC12: not currently supported since I don't have one. But probably not hard to add

See also: https://github.com/JohnDMcMaster/gxs700

## Installation

Requirements and strong recommendations:
  * Faxitron x-ray as found on DX-50 (and maybe MX-20)
  * Hammamatsu C9730DK-11 sensor as found on DX-50 w/ DC5 option
  * Ubuntu 16.04 x64. While code is cross platform, Ubuntu at least is strongly reccomended during early testing
  * USB serial converter

```
sudo apt-get install -y python3-numpy python3-scipy python3-pil python3-serial
sudo pip3 install libusb1
./udev.sh
sudo usermod -a -G plugdev $USER

# Optional
sudo apt-get install -y imagemagick
```

You may need to restart your computer for changes to take effect.

Plug in the sensor USB and use a USB serial converter to connect to the x-ray (default: /dev/ttyUSB0)

Verify installation by checking communication:

```
python3 dump.py
```

Then if you wish close the door and take an uncalibrated x-ray:

```
python3 main.py --raw
```

Images will be stored to directory "out". However, to get good images you should run calibration instead of just capturing raw images

## Collect diagnostic information

If you can please run:
```
python3 dump.py
```
And send the resulting "dump" folder to JohnDMcMaster at gmail.com. It would also be nice if you can include your cal folder so I can also get a better idea of common sensor issues


## Calibration

Some general notes:
* Use configuration you'll want to image in (ex: ensure sensor is clean, sample holder present, etc)
* 2000 ms exposure default
* 35 kVp default
* About 4 images is good to reduce noise, with slight improvement at 8. Beyond that there is minor improvement. As such capture default is 8, but for calibration we collect more

```
./cal.sh
```

This should write some files to the folder "cal". Take a look at the bad pixel map (bad.png) to see if it looks reasonable.
Compare it to the histogram equalized flat field (ff) and dark field images to see if any pixels should be added to it manually.

Other: a bad pixel is currently defined as one that fails to cover at least 25% range. This was chosen fairly arbitrarily and could probably use more thought

## Imaging

After calibration you no longer need --raw:

```
python3 main.py
```
Note that raw images (in subdirs) are stored raw while the final output image is process. The correction pipeline is roughly:
* Average all captured images together to reduce noise
* Scale image based on flat and dark field images to increase range
* Replace bad pixels to remove visual artifacts
* Save image (".png")
* Histogram equalization (selectable algorithm: conventional or dynamic)
* Save image ("_e.png")

## Histogram equalization

We've experimented briefly with algorithms. As of 2019-12-27, there are two modes availible
which can be changed through environment variable FAXITRON_EQ_MODE. ie

```
export FAXITRON_EQ_MODE=convert
```

0 (default)
* ROI supported
* not dynamic

convert
* Use the ImageMagick convert command. This is a dynamic algorithm

See also: https://github.com/JohnDMcMaster/faxitron/issues/7

## DCAM compatibility
Some early experiments used Hamamatsu DCAM data (ie .img file). However, I basically consider that data obsolete with this utility now. That said, there's still a basic "decode_dcam.py" script if you need to convert to .png

