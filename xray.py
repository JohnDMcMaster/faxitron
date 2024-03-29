#!/usr/bin/env python3

from faxitron import xray
import argparse


def run():
    pass


def main():
    parser = argparse.ArgumentParser(description='Control Faxitron xray unit')
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--info', action="store_true")
    parser.add_argument('--timed', default=None, type=int)
    parser.add_argument('--time', default=None, type=float)
    parser.add_argument('--kvp', default=None, type=int)
    parser.add_argument('--remote', default=None, action='store_true')
    #parser.add_argument('--panel', default=None, action='store_true')
    parser.add_argument('--fire', action="store_true")
    parser.add_argument('--port', default=xray.default_port())
    args = parser.parse_args()

    xr = xray.XRay(port=args.port, verbose=args.verbose)

    if args.info:
        print("Device %s, version %s" % (xr.get_device(), xr.get_revision()))
        print("Front panel mode: %s " % xr.get_mode())
        print("State: %s" % xr.get_state())
        print("Exposure time %u ds" % xr.get_timed())
        print("kVp %u" % xr.get_kvp())

    if args.remote:
        xr.mode_remote()

    #if args.panel:
    #    xr.mode_panel()

    if args.timed:
        xr.set_timed(args.timed)

    if args.time:
        xr.set_time(args.time)

    if args.kvp:
        xr.set_kvp(args.kvp)

    # Make sure this is last to setup parameters first
    if args.fire:
        xr.fire(verbose=True)

    print('Done')


if __name__ == "__main__":
    main()
