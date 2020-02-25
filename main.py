#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import util
from faxitron import im_util
from faxitron import xray
import ham_raw
import ham_process
import os

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    parser.add_argument('--kvp', default=35, type=int)
    parser.add_argument('--port', default="/dev/ttyUSB0")
    parser.add_argument('--verbose', action="store_true")
    add_bool_arg(parser, '--bin', default=False, help='Write .bin raw data capture')
    add_bool_arg(parser, '--png', default=True, help='Write normal .png image file')
    parser.add_argument('--dir', default=None, help='Output dir')
    # Quick test shows that pretty significant improvement until about 4, then drops off
    # seems pretty diminished beyond around 8
    parser.add_argument('-n', default=8, type=int, help='Number images')
    parser.add_argument('--exp', default=2000, type=int, help='Exposure ms')
    parser.add_argument('--postfix', default=None, help='')
    parser.add_argument('--cal-dir', default=None, help='')
    # Generally the center is the most interesting
    parser.add_argument('--hist-eq-roi', default="258,258,516,516", help='hist eq x1,y1,x2,y2')
    add_bool_arg(parser, "--hist-eq", default=True)
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

    fire_verbose = True
    xr and xr.fire_begin(verbose=fire_verbose)
    try:
        ham_raw.run(outdir=outdir, postfix=args.postfix, imgn=args.n, exp=args.exp)
    # notably ^C can cause this
    finally:
        xr and xr.fire_abort(verbose=fire_verbose)

    ham_process.run(outdir, args.fn_out, cal_dir=args.cal_dir, hist_eq=args.hist_eq, raw=args.raw, hist_eq_roi=im_util.parse_roi(args.hist_eq_roi))
    
    print("done")

if __name__ == "__main__":
    main()
