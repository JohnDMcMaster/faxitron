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
from PIL import Image
import numpy as np
import os
import sys
import time
import usb1

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    parser.add_argument('--images', type=int, default=0, help='Only take first n images, for debugging')
    parser.add_argument('--cal-dir', default='cal', help='')
    parser.add_argument('dir_in', help='')
    parser.add_argument('fn_out', default=None, nargs='?', help='')
    args = parser.parse_args()

    cal_dir = args.cal_dir
    if not args.fn_out:
        dir_in = args.dir_in
        if dir_in[-1] == '/':
            dir_in = dir_in[:-1]
        fn_out = dir_in + '.png'
    else:
        fn_out = args.fn_out


    _imgn, img_in = util.average_dir(args.dir_in)


    badimg = Image.open(os.path.join(args.cal_dir, 'bad.png'))
    ffimg = Image.open(os.path.join(args.cal_dir, 'ff.png'))
    np_ff2 = np.array(ffimg)
    dfimg = Image.open(os.path.join(args.cal_dir, 'df.png'))
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

    def process(desc, im_in, fn_out):
        print('Processing %s' % desc)
        np_in2 = np.array(im_in)
        np_scaled = (np_in2 - mins) * cal_scalar
        # If it clipped, squish to good values
        np_scaled = np.minimum(np_scaled, u16_maxs)
        np_scaled = np.maximum(np_scaled, u16_mins)
        imc = Image.fromarray(np_scaled).convert("I")
        imc.save(fn_out)
    process(args.dir_in, img_in, fn_out)

    '''
    if os.path.isdir(args.din):
        if not os.path.exists(args.dout):
            os.mkdir(args.dout)

        for fn_in in glob.glob(args.din + '/*.png'):
            fn_out = os.path.join(args.dout, os.path.basename(fn_in))
            process(fn_in, fn_out)
    elif os.path.isfile(args.din):
        fn_in = args.din
        fn_out = args.dout
        if not fn_out:
            fn_out = fn_in.replace('.png', '_cal.png')
            assert fn_in != fn_out
        process(fn_in, fn_out)
    else:
        raise Exception("Bad input file/dir")
    '''



    print("done")

if __name__ == "__main__":
    main()
