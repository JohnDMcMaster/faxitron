#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import ham
from faxitron import util
import os

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('fin', help='')
    args = parser.parse_args()

    buff = open(args.fin, 'r').read()
    vendor, model, ver, sn = ham.parse_info(buff)
    print("Vendor: %s" % vendor)
    print("Model: %s" % model)
    print("Version: %s" % ver)
    print("S/N: %s" % sn)

if __name__ == "__main__":
    main()
