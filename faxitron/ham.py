#!/usr/bin/env python3

import binascii
import datetime
import time
import usb1
from faxitron.util import hexdump, add_bool_arg, tobytes
from PIL import Image
import os
import struct

imgsz = 1032 * 1032 * 2

def validate_read(expected, actual, msg):
    expected = tobytes(expected)
    actual = tobytes(actual)
    if expected != actual:
        print('Failed %s' % msg)
        print('  Expected; %s' % binascii.hexlify(expected,))
        print('  Actual:   %s' % binascii.hexlify(actual,))
        raise Exception('failed validate: %s' % msg)

def bulk1(dev, cmd):
    def bulkWrite(endpoint, data, timeout=None):
        dev.bulkWrite(endpoint, tobytes(data), timeout=(1000 if timeout is None else timeout))

    def bulkRead(endpoint, length, timeout=None):
        ret = dev.bulkRead(endpoint, length, timeout=(1000 if timeout is None else timeout))
        if 0:
            print('')
            hexdump(ret, label='bulkRead(%u)' % length, indent='')
        return ret

    bulkWrite(0x01, cmd)
    return bulkRead(0x83, 0x0200)

def get_info(dev):
    '''
    00000000  48 41 4D 41 4D 41 54 53  55 00 00 00 00 00 00 00  |HAMAMATSU.......|
    00000010  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    00000020  43 39 37 33 30 44 4B 2D  31 31 00 00 00 00 00 00  |C9730DK-11......|
    00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    00000040  31 2E 32 31 00 00 00 00  00 00 00 00 00 00 00 00  |1.21............|
    00000050  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    00000060  35 34 30 33 32 31 39 00  00 00 00 00 00 00 00 00  |5403219.........|
    00000070  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
    '''
    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x00\x00\x00\x00\x00"), "packet 209/210")
    ret = bulk1(dev, b"\x00\x00\x00\x01\x00\x00\x00\x00")
    assert len(ret) == 0x80
    return ret

def init(dev, exp_ms=500):
    def bulkRead(endpoint, length, timeout=None):
        ret = dev.bulkRead(endpoint, length, timeout=(1000 if timeout is None else timeout))
        print('')
        hexdump(ret, label='bulkRead(%u)' % length, indent='')
        return ret

    def bulkWrite(endpoint, data, timeout=None):
        dev.bulkWrite(endpoint, data, timeout=(1000 if timeout is None else timeout))
    
    def controlRead(request_type, request, value, index, length,
                    timeout=None):
        return dev.controlRead(request_type, request, value, index, length,
                    timeout=(1000 if timeout is None else timeout))

    def controlWrite(request_type, request, value, index, data,
                     timeout=None):
        dev.controlWrite(request_type, request, value, index, data,
                     timeout=(1000 if timeout is None else timeout))


    '''
    # Generated from packet 209/210
    bulkWrite(0x01, "\x00\x00\x00\x00\x00\x00\x00\x00")
    # Generated from packet 211/212
    buff = bulkRead(0x83, 0x0200)
    validate_read(b"\x01", buff, "packet 211/212")
    '''
    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x00\x00\x00\x00\x00"), "packet 211/212")

    get_info(dev)
    validate_read(
            "\x00\x00\x00\x14\x00\x00\x04\x08\x00\x00\x04\x08\x00\x00\x00\x10" \
            "\x00\x00\x00\x01"
            , bulk1(dev, b"\x00\x00\x00\x02\x00\x00\x00\x00"), "packet 217/218")
    validate_read(b"\x00\x00\x00\x06\x00\x00\x00\x20\x00\x00\x00\x03", bulk1(dev, b"\x00\x00\x00\x24\x00\x00\x00\x00"), "packet 221/222")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2A\x00\x00\x00\x00"), "packet 225/226")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x39\x00\x00\x00\x00"), "packet 229/230")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x3A\x00\x00\x00\x00"), "packet 233/234")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x3B\x00\x00\x00\x00"), "packet 237/238")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x3C\x00\x00\x00\x00"), "packet 241/242")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x3D\x00\x00\x00\x00"), "packet 245/246")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x4A\x00\x00\x00\x00"), "packet 249/250")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x4F\x00\x00\x00\x00"), "packet 253/254")
    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x23\x00\x00\x00\x00"), "packet 257/258")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x29\x00\x00\x00\x00"), "packet 261/262")
    validate_read(b"\x01", bulk1(dev, 
            "\x00\x00\x00\x09\x00\x00\x00\x0A\x00\x01\x00\x00\x00\x00\x04\x08" \
            "\x04\x08"
            ), "packet 277/278")
    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 281/282")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2E\x00\x00\x00\x04\x00\x00\x00\x02"), "packet 285/286")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2E\x00\x00\x00\x04\x00\x00\x00\x12"), "packet 289/290")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2E\x00\x00\x00\x04\x00\x00\x00\x18"), "packet 293/294")
    validate_read(b"\x3F\x9E\xB8\x51\xEB\x85\x1E\xB8", bulk1(dev, b"\x00\x00\x00\x21\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 297/298")
    validate_read(b"\x40\x34\x00\x00\x00\x00\x00\x00", bulk1(dev, b"\x00\x00\x00\x21\x00\x00\x00\x04\x00\x00\x00\x01"), "packet 301/302")
    validate_read(b"\x3F\x50\x62\x4D\xD2\xF1\xA9\xFC", bulk1(dev, b"\x00\x00\x00\x21\x00\x00\x00\x04\x00\x00\x00\x02"), "packet 305/306")
    validate_read(b"\x00\x00\x00\x00\x00\x00\x00\x00", bulk1(dev, b"\x00\x00\x00\x21\x00\x00\x00\x04\x00\x00\x00\x03"), "packet 309/310")


    set_exp(dev, exp_ms)
    assert get_exp(dev) == exp_ms


    trig_int(dev)


    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2E\x00\x00\x00\x04\x00\x00\x00\x12"), "packet 345/346")
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2E\x00\x00\x00\x04\x00\x00\x00\x02"), "packet 349/350")

    set_exp(dev, exp_ms)


    trig_int(dev)


    validate_read(b"\x01", bulk1(dev, 
        "\x00\x00\x00\x09\x00\x00\x00\x0A\x00\x01\x00\x00\x00\x00\x04\x08" \
        "\x04\x08"
        ), "packet 1290/1291")


    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 1294/1295")


    validate_read(b"\x01", bulk1(dev, 
        "\x00\x00\x00\x09\x00\x00\x00\x0A\x00\x01\x00\x00\x00\x00\x04\x08" \
        "\x04\x08"
        ), "packet 1290/1291")


    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 1294/1295")
    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 1294/1295")

    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x0E\x00\x00\x00\x01\x01"), "packet 1398/1399")

def cap_img(dev, timeout_ms=2500):
    def bulkRead(endpoint, length, timeout=None):
        return dev.bulkRead(endpoint, length, timeout=timeout_ms)

    '''
    Ret buff 1: 2
    Ret buff 132: 130
    Ret buff 133: 6

    Ret buff 134: 2
    Ret buff 265: 130
    Ret buff 266: 6

    Ret buff 267: 2
    Ret buff 398: 130
    Ret buff 399: 6


    Others are 16384
    131 * 16384 = 2146304
    '''

    pack2 = bulkRead(0x82, 0x4000)
    assert len(pack2) == 2, len(pack2)
    hexdump(pack2)

    '''
    pack130 = bulkRead(0x82, 0x4000)
    assert len(pack130) == 130, len(pack130)
    buff = bytearray()
    for i in range(131):
        buff += bulkRead(0x82, 0x4000)
    pack6 = bulkRead(0x82, 0x4000)
    assert len(pack6) == 6
    return buff
    '''
    
    buff = bytearray()
    while True:
        pack = bulkRead(0x82, 0x4000)
        if len(pack) == 6:
            return pack2, buff
        else:
            buff += pack

def decode(buff):
    '''Given bin return PIL image object'''
    depth = 2
    width, height = 1032, 1032
    buff = bytearray(buff)
    assert len(buff) == width * height * depth

    # no need to reallocate each loop
    img = Image.new("I", (height, width), "White")

    for y in range(height):
        line0 = buff[y * width * depth:(y + 1) * width * depth]
        for x in range(width):
            b0 = line0[2*x + 0]
            b1 = line0[2*x + 1]
            img.putpixel((x, y), (b1 << 8) + b0)
    return img

def trig_sync(dev):
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2D\x00\x00\x00\x02\x00\x05"), "packet 61/62")

def trig_int(dev):
    validate_read(b"\x00", bulk1(dev, b"\x00\x00\x00\x2D\x00\x00\x00\x02\x00\x01"), "packet 61/62")

def pack32(n):
    return struct.pack('>I', n)

def unpack32(buff):
    return struct.unpack('>I', buff)[0]

def get_exp(dev):
    return unpack32(bulk1(dev, b"\x00\x00\x00\x1F\x00\x00\x00\x00"))

def set_exp(dev, exp_ms):
    # Determined experimentally
    # less than 30 verify fails
    # setting above 2000 seems to silently fail and peg at 2000
    # 3000 is slightly brighter than 2000 though, so the actual limit might be 2048 or something of that sort
    assert 30 <= exp_ms <= 2000

    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x20\x00\x00\x00\x04" + pack32(exp_ms)), "exposure set")
    assert get_exp(dev) == exp_ms
   
    validate_read(b"\x01", bulk1(dev,
            b"\x00\x00\x00\x09\x00\x00\x00\x0A\x00\x01\x00\x00\x00\x00\x04\x08" \
            b"\x04\x08"
            ), "packet 925/926")
    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 929/930")
    validate_read(b"\x01", bulk1(dev,
            b"\x00\x00\x00\x09\x00\x00\x00\x0A\x00\x01\x00\x00\x00\x00\x04\x08" \
            b"\x04\x08"
            ), "packet 933/934")
    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 937/938")
    validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", bulk1(dev, b"\x00\x00\x00\x04\x00\x00\x00\x00"), "packet 941/942")

    # adding this seems to actually confirm the exposure
    # tried removing and old is in place without it
    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x0E\x00\x00\x00\x01\x01"), "packet 945/946")


def open_dev(usbcontext=None):
    if usbcontext is None:
        usbcontext = usb1.USBContext()
    
    print('Scanning for devices...')
    for udev in usbcontext.getDeviceList(skip_on_error=True):
        vid = udev.getVendorID()
        pid = udev.getProductID()
        if (vid, pid) == (0x0661, 0xA802):
            print('')
            print('')
            print('Found device')
            print('Bus %03i Device %03i: ID %04x:%04x' % (
                udev.getBusNumber(),
                udev.getDeviceAddress(),
                vid,
                pid))
            return udev.open()
    raise Exception("Failed to find a device")

class Hamamatsu:
    def __init__(self, exp_ms=250):
        usbcontext = usb1.USBContext()
        self.dev = open_dev(usbcontext)
        self.dev.claimInterface(0)
        self.dev.resetDevice()
        self.exp_ms = exp_ms
        init(self.dev, exp_ms=self.exp_ms)

    def cap(self, cb, n=1):
        buffs=[]
        print("Collecting")
        for i in range(n):
            print("img %u" % i)
            pack2, buff = cap_img(self.dev, timeout_ms=(self.exp_ms + 500))
            assert len(buff) == imgsz + 2, len(buff)
            postfix = buff[imgsz:]
            buff = buff[0:imgsz]
            buffs.append(buff)
        print("Dispatching")
        for i in range(n):
            print("img %u" % i)
            cb(i, buffs[i])
        print("exp: %u" % get_exp(self.dev))

    def set_exp(self, ms):
        self.exp_ms = ms
        set_exp(self.dev, ms)

