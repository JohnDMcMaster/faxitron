#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import xray
from faxitron import ham
import os
import time

def run_cap(outdir, prefix, postfix, imgn, bin_out=False, png_out=True, exp=2000, verbose=False):
    if not outdir:
        outdir = default_date_dir("out", "", postfix)

    def cap_cb(n, buff):
        binfn = os.path.join(outdir, "%s%02u.bin" % (prefix, n))
        pngfn = os.path.join(outdir, "%s%02u.png" % (prefix, n))
        
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
    parser.add_argument('--kvp', default=35, type=int)
    parser.add_argument('--port', default="/dev/ttyUSB0")
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--dir', default=None, help='Output dir')
    # Quick test shows that pretty significant improvement until about 4, then drops off
    # seems pretty diminished beyond around 8
    parser.add_argument('-n', default=8, type=int, help='Number images per burst')
    parser.add_argument('-m', default=1, type=int, help='Number image bursts')
    parser.add_argument('-t', default=60, type=int, help='Burst period')
    parser.add_argument('--exp', default=2000, type=int, help='Exposure ms')
    parser.add_argument('--postfix', default=None, help='')
    # Generally the center is the most interesting
    add_bool_arg(parser, "--raw", default=False)
    parser.add_argument('fn_out', default=None, nargs='?', help='')
    args = parser.parse_args()

    outdir = args.dir
    if outdir is None:
        outdir = default_date_dir("out", "", args.postfix)

    if args.kvp:
        xr = xray.XRay(port=args.port, verbose=args.verbose)
        mkdir_p(outdir)
        xr.write_json(outdir)
        xr.set_kvp(args.kvp)    
        # FIXME: do something more intelligment
        xr.set_time(300)
    else:
        xr = None

    tnext = time.time()
    for capm in range(args.m):
        print("Waiting %u sec until next burst" % (time.time() - tnext,))
        while time.time() < tnext:
            time.sleep(0.1)
        print("")
        print("Burst %s" % capm)
        print("Burst %s" % capm)
        prefix = "cap_%02u_" % capm
        fire_verbose = True
        xr and xr.fire_begin(verbose=fire_verbose)
        try:
            run_cap(outdir=outdir, prefix=prefix, postfix=args.postfix, imgn=args.n, exp=args.exp)
        # notably ^C can cause this
        finally:
            xr and xr.fire_abort(verbose=fire_verbose)
        tnext += args.t

    print("done")

if __name__ == "__main__":
    main()
