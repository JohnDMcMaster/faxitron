#!/usr/bin/env python3

from faxitron.util import add_bool_arg, default_date_dir, mkdir_p
from faxitron import ham
from faxitron import im_util
import os

def main():
    import argparse 
    
    parser = argparse.ArgumentParser(description='Get default calibration file directory for attached sensor')
    args = parser.parse_args()

    h = ham.Hamamatsu()
    print(im_util.default_cal_dir(j=h.get_json()))

if __name__ == "__main__":
    main()
