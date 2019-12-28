#!/usr/bin/env python3

import binascii
import time
import usb1
from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from PIL import Image
import os
from faxitron import ham
import glob

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    add_bool_arg(parser, '--bin', default=False, help='Write .bin raw data capture')
    add_bool_arg(parser, '--png', default=True, help='Write normal .png image file')
    parser.add_argument('--dir', default=None, help='Output dir')
    parser.add_argument('-n', default=1, type=int, help='Number images')
    parser.add_argument('--exp', default=2000, type=int, help='Exposure ms')
    parser.add_argument('--postfix', default=None, help='')
    args = parser.parse_args()

    outdir = args.dir
    if outdir is None:
        outdir = default_date_dir("out", "", args.postfix)

    def cap_cb(n, buff):
        binfn = os.path.join(outdir, "cap_%02u.bin" % n)
        pngfn = os.path.join(outdir, "cap_%02u.png" % n)
        
        if args.bin:
            print("Saving %s" % binfn)
            open(binfn, 'w').write(buff)
        if args.png:
            print("Saving %s" % pngfn)
            ham.decode(buff).save(pngfn)

    h = ham.Hamamatsu()
    mkdir_p(outdir)
    h.set_exp(args.exp)

    print('')
    print('')
    print('')

    h.cap(cap_cb, n=args.n)
    

if __name__ == "__main__":
    main()

