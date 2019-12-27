#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import ham
from faxitron import util

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    parser.add_argument('--dir', default=None, help='Output dir')
    parser.add_argument('--postfix', default=None, help='')
    args = parser.parse_args()

    outdir = args.dir
    if outdir is None:
        outdir = default_date_dir("dump", "", args.postfix)

    h = ham.Hamamatsu()
    mkdir_p(outdir)
    info = ham.get_info(h.dev)
    util.hexdump(info)
    fn = "%s/info.bin" % outdir
    print("Writing %s" % fn)
    open(fn, "wb").write(info)

if __name__ == "__main__":
    main()
