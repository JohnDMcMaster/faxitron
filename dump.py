#!/usr/bin/env python3

from faxitron.util import default_date_dir, mkdir_p
from faxitron import ham
from faxitron import util
from faxitron import xray
import os
import json

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Dump diagnostic info')
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--dir', default=None, help='Output dir')
    parser.add_argument('--postfix', default=None, help='')
    parser.add_argument('--port', default=xray.default_port())
    util.add_bool_arg(parser, '--ham', default=True, help='Include sensor output')
    args = parser.parse_args()

    outdir = args.dir
    if outdir is None:
        outdir = default_date_dir("dump", "", args.postfix)
    mkdir_p(outdir)
    _iolog = util.IOLog(out_fn=os.path.join(outdir, 'out.txt'))
    print("Writing to %s" % outdir)

    if args.ham:
        print("")
        print("Sensor")
        h = ham.Hamamatsu()
    
        info = ham.get_info(h.dev)
        # util.hexdump(info)
        vendor, model, ver, sn = ham.parse_info(info)
        print("Vendor: %s" % vendor)
        print("Model: %s" % model)
        print("Version: %s" % ver)
        print("S/N: %s" % sn)
        fn = os.path.join(outdir, "ham_info.bin")
        print("Writing %s" % fn)
        open(fn, "w").write(info)

    if args.port:
        print("")
        print("X-ray")
        xr = xray.XRay(port=args.port, verbose=args.verbose)

        j = {
            "dev": xr.get_device(),
            "rev": xr.get_revision(),
            "mode": xr.get_mode(),
            "state": xr.get_state(),
            "timed": xr.get_timed(),
            "kvp": xr.get_kvp(),
        }
        print("Device %s, version %s" % (j["dev"], j["rev"]))
        print("Front panel mode: %s " % j["mode"])
        print("State: %s" % j["state"])
        print("Exposure time %u ds" % j["timed"])
        print("kVp %u" % j["kvp"])
        fn = os.path.join(outdir, "xray.json")
        print("Writing %s" % fn)
        open(fn, 'w').write(json.dumps(j, sort_keys=True, indent=4, separators=(',', ': ')))

if __name__ == "__main__":
    main()
