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
from faxitron.util import width, height, depth

import binascii
import glob
from PIL import Image, ImageOps
import numpy as np
import os
import sys
import time
import usb1
from scipy.ndimage import median_filter
import statistics

def make_bpm(im):
    ret = set()
    for y in range(height):
        for x in range(width):
            if im.getpixel((x, y)):
                ret.add((x, y))
    return ret


def im_med3(im, x, y):
    pixs = []
    for dx in range(-1, 2, 1):
        xp = x + dx
        if xp < 0 or xp >= width:
            continue
        for dy in range(-1, 2, 1):
            yp = y + dy
            if yp < 0 or yp >= height:
                continue
            pixs.append(im.getpixel((xp, yp)))
    return statistics.median(pixs)


def do_bpr(im, badimg):
    ret = im.copy()
    bad_pixels = make_bpm(badimg)
    for x, y in bad_pixels:
        ret.putpixel((x, y), im_med3(im, x, y))
    return ret

def run(dir_in, fn_out, cal_dir="cal", hist_eq=True, invert=True, hist_eq_roi=None, scalar=None):
    cal_dir = cal_dir
    if not fn_out:
        dir_in = dir_in
        if dir_in[-1] == '/':
            dir_in = dir_in[:-1]
        fn_out = dir_in + '.png'
        fn_oute = dir_in + '_e.png'
    else:
        fn_out = fn_out
        fn_oute = fn_out


    _imgn, img_in = util.average_dir(dir_in, scalar=scalar)

    rescale = False
    bpr = True

    badimg = Image.open(os.path.join(cal_dir, 'bad.png'))
    
    desc = dir_in
    print('Processing %s' % desc)
    
    im_wip = img_in
    if rescale:
        ffimg = Image.open(os.path.join(cal_dir, 'ff.png'))
        np_ff2 = np.array(ffimg)
        dfimg = Image.open(os.path.join(cal_dir, 'df.png'))
        np_df2 = np.array(dfimg)

        # ff *should* be brighter than df
        # (due to .png pixel value inversion convention)
        mins = np.minimum(np_df2, np_ff2)
        maxs = np.maximum(np_df2, np_ff2)
    
        u16_mins = np.full(mins.shape, 0x0000, dtype=np.dtype('float'))
        u16_ones = np.full(mins.shape, 0x0001, dtype=np.dtype('float'))
        u16_maxs = np.full(mins.shape, 0xFFFF, dtype=np.dtype('float'))
    
        cal_det = maxs - mins
        # Prevent div 0 on bad pixels
        cal_det = np.maximum(cal_det, u16_ones)
        cal_scalar = 0xFFFF / cal_det

        np_in2 = np.array(im_wip)
        np_scaled = (np_in2 - mins) * cal_scalar
        # If it clipped, squish to good values
        np_scaled = np.minimum(np_scaled, u16_maxs)
        np_scaled = np.maximum(np_scaled, u16_mins)
        im_wip = Image.fromarray(np_scaled).convert("I")

    if bpr:
        im_wip = do_bpr(im_wip, badimg)

    if invert:
        # IOError("not supported for this image mode")
        # im_wip = ImageOps.invert(im_wip)
        im_wip = util.im_inv16_slow(im_wip)
    im_wip.save(fn_out)


    if hist_eq:
        if hist_eq_roi:
            x1, y1, x2, y2 = hist_eq_roi
            ref_im = im_wip.crop((x1, y1, x2, y2))
        else:
            ref_im = im_wip

        ref_np2 = np.array(ref_im)
        wip_np2 = np.array(im_wip)
        wip_np2 = util.histeq_np_apply(wip_np2, util.histeq_np_create(ref_np2))
        im_wip = util.npf2im(wip_np2)
        im_wip.save(fn_oute)

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    #parser.add_argument('--images', type=int, default=0, help='Only take first n images, for debugging')
    parser.add_argument('--cal-dir', default='cal', help='')
    parser.add_argument('--hist-eq-roi', default=None, help='hist eq x1,y1,x2,y2')
    add_bool_arg(parser, "--hist-eq", default=True)
    add_bool_arg(parser, "--invert", default=True)
    parser.add_argument('--scalar', default=None, type=float, help='')
    parser.add_argument('dir_in', help='')
    parser.add_argument('fn_out', default=None, nargs='?', help='')
    args = parser.parse_args()

    run(args.dir_in, args.fn_out, cal_dir=args.cal_dir, hist_eq=args.hist_eq, invert=args.invert, hist_eq_roi=util.parse_roi(args.hist_eq_roi), scalar=args.scalar)

    print("done")

if __name__ == "__main__":
    main()
