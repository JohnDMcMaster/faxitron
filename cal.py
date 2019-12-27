#!/usr/bin/env python3

"""
Looking over:
https://stackoverflow.com/questions/18951500/automatically-remove-hot-dead-pixels-from-an-image-in-python
Suggests take the median of the surrounding pixels

Lets just create an image map with the known bad pixels
Arbitrarily going to set to black to good pixel, white for bad pixel
"""

from faxitron.util import hexdump, add_bool_arg, default_date_dir, mkdir_p
from faxitron import ham
from faxitron import util

import binascii
import glob
from PIL import Image
import numpy as np
import os
import sys
import time
import usb1

depth = 2
height, width = 1032, 1032

def average_dir(din, images=0):
    pixs = width * height
    imgs = []
    print('Reading %s' % din)
    for fni, fn in enumerate(glob.glob(din + "/cap_*.png")):
        imgs.append(Image.open(fn))
        if images and fni + 1 >= images:
            break

    statef = np.zeros((height, width), np.float)
    for im in imgs:
        statef = statef + np.array(im, dtype=np.float) / len(imgs)
    #return statef, None
    rounded = np.round(statef)
    #print("row1: %s" % rounded[1])
    statei = np.array(rounded, dtype=np.uint16)
    #print(len(statei), len(statei[0]), len(statei[0]))

    # for some reason I isn't working correctly
    # only L
    #im = Image.fromarray(statei, mode="I")
    #im = Image.fromarray(statei, mode="L")
    # workaround by plotting manually
    im = Image.new("I", (height, width), "Black")
    for y, row in enumerate(statei):
        for x, val in enumerate(row):
            # this causes really weird issues if not done
            val = int(val)
            im.putpixel((x, y), val)
            if 0 and y == 0 and x < 16:
                print(x, y, val, im.getpixel((x, y)))
                im.putpixel((x, y), val)

    return statef, im


"""
def bad_pixs_bf1(bff, bfi):
    bfmed = np.median(bff)
    print("min: %0.1f, med: %0.1f, max: %0.1f" % (np.amin(bff), bfmed, np.amax(bff)))
    #cold_pixs = bff[bff <= bfmed/2.0]
    cold_pixs = np.nonzero(bff <= bfmed/2.0)
    print(cold_pixs)
    print("Cold pixels: %u / %u" % (len(cold_pixs), width * height))
    #x = i % width
    #y = i // width
"""

def bad_pixs_bf(bff, bfi):
    bfmed = np.median(bff)
    print("min: %0.1f, med: %0.1f, max: %0.1f" % (np.amin(bff), bfmed, np.amax(bff)))

    ret = []
    thresh = bfmed * 0.25
    for y in range(height):
        for x in range(width):
            val = bfi.getpixel((x, y))
            if 0 and y == 0 and x < 16:
                print(x, y, val)
            if val <= thresh:
                ret.append((x, y))

    print("Cold pixels: %u / %u" % (len(ret), width * height))
    return ret

def bad_pixs_df(bff, bfi):
    bfmed = np.median(bff)
    print("min: %0.1f, med: %0.1f, max: %0.1f" % (np.amin(bff), bfmed, np.amax(bff)))

    ret = []
    thresh = 0xFFFF * 0.25
    for y in range(height):
        for x in range(width):
            val = bfi.getpixel((x, y))
            if 0 and y == 0 and x < 16:
                print(x, y, val)
            if val >= thresh:
                ret.append((x, y))

    print("Hot pixels: %u / %u" % (len(ret), width * height))
    return ret

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    parser.add_argument('--images', type=int, default=0, help='Only take first n images, for debugging')
    parser.add_argument('bf_dir', help='')
    parser.add_argument('df_dir', help='')
    parser.add_argument('cal_dir', help='')
    args = parser.parse_args()
    
    cal_dir = args.cal_dir
    badimg = Image.new("1", (height, width), "Black")

    bff, bfi = average_dir(args.bf_dir, images=args.images)
    bfi.save(cal_dir + '/bf.png')
    util.histeq_im(bfi).save(cal_dir + '/bfe.png')
    for x, y in bad_pixs_bf(bff, bfi):
        badimg.putpixel((x, y), 1)

    dff, dfi = average_dir(args.df_dir, images=args.images)
    dfi.save(cal_dir + '/df.png')
    util.histeq_im(dfi).save(cal_dir + '/dfe.png')
    for x, y in bad_pixs_df(dff, dfi):
        badimg.putpixel((x, y), 1)

    badimg.save(cal_dir + '/bad.png')

    #dff, dfi = average_dir(args.df_dir)
    
    print("done")

if __name__ == "__main__":
    #im = Image.fromarray(np.asarray([[1, 2, 3], [4, 5, 6]]), mode="I")
    #im.show()
    main()

