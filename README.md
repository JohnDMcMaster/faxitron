For Faxitron DX-50 x-ray w/ DC5 option. Other systems may be supported in the future. Short term goal is to be able to control x-ray and decode images. Images are currently captured using Hamamatsu utility

For more information: https://nucwiki.org/wiki/index.php/Faxitron

python decode.py  img/3/3_0.{img,tif}

convert img/3/3_0.tif img/3/3_2.tif img/3/3_2.tif -compose Plus -composite img/3/3_c.tif

convert img/3/3_c.tif \( +clone -equalize \) -average img/3/3_e.jpg

