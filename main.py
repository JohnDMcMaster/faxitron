#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import ham
from faxitron import util
from faxitron import xray
import ham_process
import os

def capture(args, outdir):
    def cap_cb(n, buff):
        binfn = os.path.join(outdir, 'cap_%02u.bin' % n)
        pngfn = os.path.join(outdir, 'cap_%02u.png' % n)
        
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
    parser.add_argument('--cal-dir', default='cal', help='')
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
        xr.set_kvp(args.kvp)    
        # FIXME: do something more intelligment
        xr.set_time(300)
    else:
        xr = None

    fire_verbose = True
    xr and xr.fire_begin(verbose=fire_verbose)
    try:
        capture(args, outdir)
    # notably ^C can cause this
    finally:
        xr and xr.fire_abort(verbose=fire_verbose)

    ham_process.run(outdir, args.fn_out, cal_dir=args.cal_dir, hist_eq=args.hist_eq, raw=args.raw, hist_eq_roi=util.parse_roi(args.hist_eq_roi))

    print("done")

if __name__ == "__main__":
    main()
