import numpy as np
from PIL import Image
import glob
import os
import json
import statistics


def parse_roi(s):
    if s is None:
        return None
    return [int(x) for x in s.split(',')]


def histeq_im(im, nbr_bins=256):
    imnp2 = np.array(im)
    imnp2_eq = histeq_np(imnp2, nbr_bins=nbr_bins)
    imf = Image.fromarray(imnp2_eq)
    return imf.convert("I")


def histeq_np(npim, nbr_bins=256):
    '''
    Given a numpy nD array (ie image), return a histogram equalized numpy nD array of pixels
    That is, return 2D if given 2D, or 1D if 1D
    '''
    return histeq_np_apply(npim, histeq_np_create(npim, nbr_bins=nbr_bins))


def histeq_np_create(npim, nbr_bins=256, verbose=0):
    '''
    Given a numpy nD array (ie image), return a histogram equalized numpy nD array of pixels
    That is, return 2D if given 2D, or 1D if 1D
    '''

    # get image histogram
    flat = npim.flatten()
    verbose and print('flat', flat)
    imhist, bins = np.histogram(flat, nbr_bins)
    verbose and print('imhist', imhist)
    verbose and print('imhist', bins)
    cdf = imhist.cumsum()  #cumulative distribution function
    verbose and print('cdfraw', cdf)
    cdf = 0xFFFF * cdf / cdf[-1]  #normalize
    verbose and print('cdfnorm', cdf)
    return cdf, bins


def histeq_np_apply(npim, create):
    cdf, bins = create

    # use linear interpolation of cdf to find new pixel values
    ret1d = np.interp(npim.flatten(), bins[:-1], cdf)
    return ret1d.reshape(npim.shape)


# Tried misc other things but this was only thing I could make work
def im_inv16_slow(im):
    '''Invert 16 bit image pixels'''
    im32_2d = np.array(im)
    im32_1d = im32_2d.flatten()
    for i, p in enumerate(im32_1d):
        im32_1d[i] = 0xFFFF - p
    ret = Image.fromarray(im32_1d.reshape(im32_2d.shape))
    return ret


def npf2im(statef):
    #return statef, None
    rounded = np.round(statef)
    #print("row1: %s" % rounded[1])
    statei = np.array(rounded, dtype=np.uint16)
    #print(len(statei), len(statei[0]), len(statei[0]))
    height = len(statef)
    width = len(statef[0])

    # for some reason I isn't working correctly
    # only L
    #im = Image.fromarray(statei, mode="I")
    #im = Image.fromarray(statei, mode="L")
    # workaround by plotting manually
    im = Image.new("I", (width, height), "Black")
    for y, row in enumerate(statei):
        for x, val in enumerate(row):
            # this causes really weird issues if not done
            val = int(val)
            im.putpixel((x, y), val)

    return im


def average_imgs(imgs, scalar=None):
    width, height = imgs[0].size
    if not scalar:
        scalar = 1.0
    scalar = scalar / len(imgs)

    statef = np.zeros((height, width), float)
    for im in imgs:
        assert (width, height) == im.size
        statef = statef + scalar * np.array(im, dtype=float)

    return statef, npf2im(statef)


def average_dir(din, images=0, verbose=1, scalar=None):
    imgs = []

    files = list(glob.glob(os.path.join(din, "cap_*.png")))
    verbose and print('Reading %s w/ %u images' % (din, len(files)))

    for fni, fn in enumerate(files):
        imgs.append(Image.open(fn))
        if images and fni + 1 >= images:
            verbose and print("WARNING: only using first %u images" % images)
            break
    return average_imgs(imgs, scalar=scalar)


def default_cal_dir(j=None, im_dir=None):
    if im_dir:
        j = json.load(open(os.path.join(im_dir, "sensor.json"), "r"))
    assert j
    """
    {
        "exp_ms": 1000,
        "model": "C9730DK-11",
        "sn": "5403219",
        "vendor": "HAMAMATSU",
        "ver": "1.21"
    }
    """
    d = "%s_%s" % (j["model"], j["sn"])
    d = d.lower()
    return os.path.join("cal", d)


def make_bpm(im):
    width, height = im.size
    ret = set()
    for y in range(height):
        for x in range(width):
            if im.getpixel((x, y)):
                ret.add((x, y))
    return ret


def im_med3(im, x, y, badimg):
    width, height = badimg.size
    pixs = []
    for dx in range(-1, 2, 1):
        xp = x + dx
        if xp < 0 or xp >= width:
            continue
        for dy in range(-1, 2, 1):
            yp = y + dy
            if yp < 0 or yp >= height:
                continue
            if not badimg.getpixel((xp, yp)):
                pixs.append(im.getpixel((xp, yp)))
    return int(statistics.median(pixs))


def do_bpr(im, badimg):
    ret = im.copy()
    bad_pixels = make_bpm(badimg)
    for x, y in bad_pixels:
        ret.putpixel((x, y), im_med3(im, x, y, badimg))
    return ret


def dir2np(din, cal_dir=None, bpr=False):
    ret = []

    badimg = None
    if bpr and cal_dir:
        badimg = Image.open(os.path.join(cal_dir, 'bad.png'))
        print("Loaded bad pixel map")

    m = 0
    while True:
        burst = []
        for fn in list(glob.glob(os.path.join(din, "cap_%02u_*.png" % m))):
            im = Image.open(fn)
            if badimg:
                im = do_bpr(im, badimg)

            npim = np.array(im, dtype=float)
            burst.append(np.ndarray.flatten(npim))
        if not burst:
            break
        ret.append(burst)
        m += 1
    return ret


def average_npimgs(npims):
    """
    width = len(npims[0])
    height = len(npims)

    statef = np.zeros((height, width), float)
    for npim in npims:
        statef = statef + npim 

    return statef / len(npims)
    """
    #return np.sum(npims, axis=0) / len(npims)
    return np.average(npims, axis=0)
