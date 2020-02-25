#!/usr/bin/env python3
"""
Given a series of pixels, calculate the RMS pixel deviation
"""

from faxitron.util import add_bool_arg
from faxitron import util
from faxitron import im_util
from faxitron import ham
from faxitron.im_util import make_bpm

from PIL import Image, ImageOps
import numpy as np
import os
import statistics
import subprocess
import json
import glob
from matplotlib import pyplot as plt

try:
    from skimage import exposure
except ImportError:
    exposure = None


def rms_npims(npims, npim_avg):
    statef = np.zeros_like(npims[0])

    for npim in npims:
        x = (npim - npim_avg)
        statef = statef + x * x

    return np.sqrt(statef / len(npims))


def run(dir_in, cal_dir=None, bpr=True):
    print('Processing %s' % dir_in)

    if not cal_dir:
        cal_dir = im_util.default_cal_dir(im_dir=dir_in)
        if not os.path.exists(cal_dir):
            print("WARNING: default calibration dir %s does not exist" %
                  cal_dir)
            cal_dir = None

    bursts = im_util.dir2np(dir_in, bpr=bpr, cal_dir=cal_dir)
    rmss = []
    avgs = []
    for bursti, npims in enumerate(bursts):

        npim_avg = im_util.average_npimgs(npims)
        avgs.append(np.median(npim_avg))

        npim_rms = rms_npims(npims, npim_avg)
        median_rms = np.median(npim_rms)
        rmss.append(median_rms)

        print(
            "% 5u   avg min: % 5u, median: % 5u, max: % 5u      RMS min %0.6f med %0.6f max %0.6f"
            % (bursti, np.ndarray.min(np.array(npim_avg)), np.median(npim_avg),
               np.ndarray.max(np.array(npim_avg)), np.ndarray.min(npim_rms),
               median_rms, np.ndarray.max(npim_rms)))
        if 0:
            plt.clf()
            plt.hist(npim_rms, bins=range(0, 10, 1))
            plt.title("histogram")
            #plt.show()
            plt.savefig("temp/rms_%02u.png" % bursti)

    if len(avgs) > 1:
        plt.plot(avgs)
        plt.show()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Calculate RMS noise')
    parser.add_argument('--cal-dir', default='cal', help='')
    add_bool_arg(parser, "--bpr", default=True)
    parser.add_argument('dir_in', help='')
    args = parser.parse_args()

    run(args.dir_in, bpr=args.bpr)

    print("done")


if __name__ == "__main__":
    main()
