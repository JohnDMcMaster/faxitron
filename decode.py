#!/usr/bin/env python

import argparse
import os
import glob
from PIL import Image
import PIL

def decode(buff):
    width, height = 1032, 1032
    buff = str(buff[0:2 * width * height])
    # http://pillow.readthedocs.io/en/3.1.x/handbook/writing-your-own-file-decoder.html
    # http://svn.effbot.org/public/tags/pil-1.1.4/libImaging/Unpack.c
    img = Image.frombytes('L', (width, height), buff, "raw", "L;16", 0, -1)
    #img =  PIL.ImageOps.invert(img)
    return img

def process_bin(fin, fout):
    print('Reading %s...' % fin)
    buff = open(fin, 'r').read()
    """
    fixed 256 byte header
    TODO: decode, or at least check magic

    00000000  44 43 41 4d 49 4d 47 00  01 00 00 00 10 00 00 00  |DCAMIMG.........|
    00000010  30 00 00 00 01 00 00 00  28 00 01 10 01 00 00 00  |0.......(.......|
    00000020  00 01 00 00 00 00 00 00  80 80 20 00 00 00 00 00  |.......... .....|
    00000030  08 04 00 00 08 04 00 00  00 00 00 00 10 08 00 00  |................|
    00000040  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    *
    00000100  e1 32 0c 36 a9 35 27 36  91 35 71 35 ae 35 48 36  |.2.6.5'6.5q5.5H6|
    """
    buff = buff[256:]
    print('Decoding image...')
    img = decode(buff)
    print('Saving %s...' % fout)
    img.save(fout)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Decode a .bin to a .png')
    parser.add_argument('fin', help='.bin file name in')
    parser.add_argument('fout', default=None, nargs='?', help='.png file name out')
    args = parser.parse_args()

    if os.path.isdir(args.fin):
        if args.fout is None:
            raise Exception("dir requires fout")
        if not os.path.exists(args.fout):
            os.mkdir(args.fout)
        for fn in glob.glob(os.path.join(args.fin, '*.bin')):
            fout = os.path.join(args.fout, os.path.basename(fn).replace('.bin', '.png'))
            process_bin(fn, fout)
    else:
        fout = args.fout
        if fout is None:
            fout = args.fin.replace('.bin', '.png')
            if args.fin == fout:
                raise Exception("Couldn't auto name output file")
        process_bin(args.fin, fout)
    print('Done')
