#!/usr/bin/env python3

import binascii
import time
import usb1
from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from PIL import Image
import os
from faxitron import ham
import glob

def run(outdir, postfix, imgn, bin_out=False, png_out=True, exp=2000, verbose=False):
    if not outdir:
        outdir = default_date_dir("out", "", postfix)

    def cap_cb(n, buff):
        binfn = os.path.join(outdir, "cap_%02u.bin" % n)
        pngfn = os.path.join(outdir, "cap_%02u.png" % n)
        
        if bin_out:
            print("Saving %s" % binfn)
            open(binfn, 'w').write(buff)
        if png_out:
            print("Saving %s" % pngfn)
            h.decode(buff).save(pngfn)

    h = ham.Hamamatsu(verbose=verbose)
    mkdir_p(outdir)
    h.write_json(outdir)
    print("Setting exposure %u ms" % exp)
    h.set_exp(exp)

    if h.verbose:
        print('')
        print('')
        print('')

    h.cap(cap_cb, n=imgn)

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    parser.add_argument('--verbose', action="store_true")
    add_bool_arg(parser, '--bin', default=False, help='Write .bin raw data capture')
    add_bool_arg(parser, '--png', default=True, help='Write normal .png image file')
    parser.add_argument('--dir', default=None, help='Output dir')
    parser.add_argument('-n', default=1, type=int, help='Number images')
    parser.add_argument('--exp', default=2000, type=int, help='Exposure ms')
    parser.add_argument('--postfix', default=None, help='')
    args = parser.parse_args()

    run(args.dir, postfix=args.postfix, imgn=args.n, bin_out=args.bin, png_out=args.png, exp=args.exp, verbose=args.verbose)

if __name__ == "__main__":
    main()
