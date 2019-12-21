#!/usr/bin/env python

import argparse
import os
import glob
from PIL import Image
import PIL
import struct

MAGIC = "DCAMIMG"

class BadMagic(Exception):
    pass

# This sort of works, but gives an 8 bit image
# Can I get it to work with mode I somehow instead?
def decode_l8(buff):
    width, height = 1032, 1032
    buff = str(buff[0:2 * width * height])
    # http://pillow.readthedocs.io/en/3.1.x/handbook/writing-your-own-file-decoder.html
    # http://svn.effbot.org/public/tags/pil-1.1.4/libImaging/Unpack.c
    img = Image.frombytes('L', (width, height), buff, "raw", "L;16", 0, -1)
    #img =  PIL.ImageOps.invert(img)
    return img

def decode(buff):
    '''Given bin return PIL image object'''
    depth = 2
    width, height = 1032, 1032
    buff = bytearray(buff)

    # no need to reallocate each loop
    img = Image.new("I", (height, width), "White")

    for y in range(height):
        line0 = buff[y * width * depth:(y + 1) * width * depth]
        for x in range(width):
            b0 = line0[2*x + 0]
            b1 = line0[2*x + 1]
            img.putpixel((x, y), (b1 << 8) + b0)
    return img
#decode = decode_l8

def process_bin(fin, fout):
    print('Reading %s...' % fin)
    buff = open(fin, 'r').read()
    """
    fixed 256 byte header
    Exposure doesn't seem to be in here
    Probably binning somewhere, hpos, vpos

    00000000  44 43 41 4d 49 4d 47 00  01 00 00 00 10 00 00 00  |DCAMIMG.........|
    00000010  30 00 00 00 01 00 00 00  28 00 01 10 01 00 00 00  |0.......(.......|
    00000020  00 01 00 00 00 00 00 00  80 80 20 00 00 00 00 00  |.......... .....|
    00000030  08 04 00 00 08 04 00 00  00 00 00 00 10 08 00 00  |................|
    00000040  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    *
    00000100  e1 32 0c 36 a9 35 27 36  91 35 71 35 ae 35 48 36  |.2.6.5'6.5q5.5H6|
    """
    header = buff[0:256]
    magic = header[0:len(MAGIC)]
    if MAGIC != magic:
        raise BadMagic()
    def u32(off):
        return struct.unpack("<I", header[off:off + 4])[0]

    # 0x08 1...maybe format version?
    file_ver = u32(0x08)
    assert file_ver == 1, file_ver

    bit_ch = u32(0x0C)
    assert bit_ch == 16, bit_ch

    # 0x10 is 48, almost like RGB 16
    # but its not...so w/e
    # oddly enough, images do capture in 3s
    # but they are per file, not sure what to make of that

    # 0x14 is 1 / not sure

    # 0x18: 268501032 ? no idea

    # a few more boring fields

    img_size = u32(0x28)
    assert img_size == 1032 * 1032 * 2, img_size

    # 0x2C 0 / not sure

    width = u32(0x30)
    height = u32(0x34)
    assert width == 1032 and height == 1032, (width, height)

    # 0x38 0 / not sure

    bytes_row = u32(0x3C)
    assert bytes_row == 1032 * 2, bytes_row

    # rest 0 / not sure


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
            dout = args.fin
        else:
            dout = args.fout

        if not os.path.exists(dout):
            os.mkdir(dout)
        for fn in glob.glob(os.path.join(args.fin, '*.img')):
            fout = os.path.join(dout, os.path.basename(fn).replace('.img', '.png'))
            process_bin(fn, fout)
    else:
        fout = args.fout
        if fout is None:
            fout = args.fin.replace('.img', '.png')
            if args.fin == fout:
                raise Exception("Couldn't auto name output file")
        process_bin(args.fin, fout)
    print('Done')
