#!/usr/bin/env python3

import binascii
import datetime
import time
import usb1
from faxitron.util import hexdump, add_bool_arg, tobytes, tostr
from PIL import Image
import os
import struct

HAM_VID = 0x0661
# C9730DK-11
DC5_PID = 0xA802
DC12_PID = 0xA800

# TODO: consider upshifting to make raw easier to see
PIX_MAX = 0x3FFF

imgsz = 1032 * 1032 * 2

# Image start
# Payload: length: image size + 2
MSG_BEGIN = 0x8002
MSG_BEGIN_SZ = 2 + imgsz
# Payload length: 2 bytes
# ex: value 3
MSG_END = 0x8004
MSG_END_SZ = 6

# Including average after
imgx_sz = imgsz + 2

def now():
    return datetime.datetime.utcnow().isoformat()

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

'''
Sample info block:

00000000  48 41 4d 41 4d 41 54 53  55 00 00 00 00 00 00 00  |HAMAMATSU.......|
00000010  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000020  43 39 37 33 30 44 4b 2d  31 31 00 00 00 00 00 00  |C9730DK-11......|
00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000040  31 2e 32 31 00 00 00 00  00 00 00 00 00 00 00 00  |1.21............|
00000050  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000060  35 34 30 33 32 31 39 00  00 00 00 00 00 00 00 00  |5403219.........|
00000070  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
'''

def parse_info(buff):
    assert len(buff) == 0x80
    vendor = buff[0x00:0x20].replace('\x00', '')
    model = buff[0x20:0x40].replace('\x00', '')
    ver = buff[0x40:0x60].replace('\x00', '')
    sn = buff[0x60:0x80].replace('\x00', '')
    return vendor, model, ver, sn

def get_info(dev):
    validate_read(b"\x01", bulk1(dev, b"\x00\x00\x00\x00\x00\x00\x00\x00"), "packet 209/210")
    ret = tostr(bulk1(dev, b"\x00\x00\x00\x01\x00\x00\x00\x00"))
    assert len(ret) == 0x80
    return ret

def ham_init(dev, exp_ms=500):
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

def check_sync(buff, verbose=True):
    syncpos = 0
    n = 0
    while len(buff):
        #if len(buff) % 1000 == 0:
        #    print(len(buff))
        pack2u = unpack16_le(buff[0:2])
        if pack2u >= 0x4000:
            verbose and print("MSG 0x%04X @ 0x%04X" % (pack2u, syncpos))
            hexdump(buff[0:16], "Sync found")
            n += 1
        buff = buff[2:]
        syncpos += 2

    return n

def is_sync(buff, verbose=True):
    pack2u = unpack16_le(buff[0:2])
    if pack2u >= 0x4000:
        verbose and print("%s MSG 0x%04X @ 0x%04X" % (now(), pack2u, 0))
        hexdump(buff[0:16], "Sync found")
        return pack2u
    else:
        return 0

# TODO: make this thread capable to always take images and suck off as needed
class CapImgN:
    def __init__(self, dev, usbcontext, n=1, verbose=1):
        self.dev = dev
        self.usbcontext = usbcontext
        self.verbose = verbose
        self.n = n
        self.state = MSG_END
        self.urb_remain = 0

        # len(self.rawbuff) < imgx_sz and len(self.messages) < 1
        self.rawbuff = None
        self.completions = []
        self.urb_max = 31

        # for debugging
        self.packets = 0
        self.running = True

    def handle_buff(self, buff):
        # Wait for begin
        if self.state == MSG_END:
            sync = is_sync(buff)
            # Can get garbage packets while waiting for begin
            if not sync:
                return
            # Might be garbage in the buffer from aggressive read
            if sync == MSG_END:
                return
            # note buffer has garbage. Might have 0's or other data
            assert sync == MSG_BEGIN, ("0x%04X" % sync)
            self.state = MSG_BEGIN
            if self.verbose:
                print("")
                print("")
                print("")
            self.rawbuff = bytearray()
            self.packets = 0
        # Wait for end
        elif self.state == MSG_BEGIN:
            sync = is_sync(buff)
            if sync:
                assert sync == MSG_END, sync
                self.process_end(buff)
                self.rawbuff = None
                self.state = MSG_END
            else:
                self.packets += 1
                self.rawbuff.extend(buff)
        else:
            assert 0, self.state

    def process_end(self, endbuff):
        buff = self.rawbuff[0:imgx_sz]
        self.rawbuff = self.rawbuff[imgx_sz:]
        rawimg = buff[0:imgsz]
        footer = buff[imgsz:]

        if self.verbose:
            hexdump(buff[1032*0:1032*0+16], "First row")
            hexdump(buff[1032*1:1032*1+16], "Second row")
            hexdump(buff[1032*1031:1032*1031+16], "Last row")
            hexdump(buff[-16:], "Last bytes")
            hexdump(footer, "Image footer")
            #hexdump(rawbuff, "Additional bytes")
            print("Additional bytes: %u" % len(self.rawbuff))
            # very slow
            # check_sync(self.rawbuff)
    
        average = struct.unpack('<H', footer)[0]
        self.verbose and print("Read (average?) value: %u / 0x%04X" % (average, average))

        """
        04 80 03 00 AE 87
        04 80 03 00 AD 87
        Image counter seems to increment per capture set
        One of the commands I'm sending during init probably increments it
        """
        opcode = unpack16_le(endbuff[0:2])
        # Rest of the message is garbage in sensor buffer
        endbuff = endbuff[0:MSG_END_SZ]
        hexdump(endbuff, "EOS")
        assert opcode == MSG_END
        status, counter = struct.unpack('<HH', endbuff[2:])
        print("Status: %u, counter: %u" % (status, counter))
        assert status == 3, status
        
        assert len(rawimg) == imgsz, (len(rawimg), imgsz)

        self.completions.append((counter, rawimg, average))

    def async_cb(self, trans):
        self.handle_buff(trans.getBuffer())

        # Beware of corruption w/ multiple URBs in END state
        if self.running and (self.state == MSG_BEGIN or self.state == MSG_END and self.urb_remain == 1):
            trans.submit()
        else:
            self.urb_remain -= 1

    def alloc_urb(self, n):
        # reference only does 31, so stay with that
        for _i in range(n):
            trans = self.dev.getTransfer()
            trans.setBulk(0x82, 0x4000, callback=self.async_cb, user_data=None, timeout=1000)
            trans.submit()
            self.trans_l.append(trans)
            self.urb_remain += 1

    def run(self, timeout_ms=2500):
        tstart = time.time()

        self.trans_l = []
        self.urb_remain = 0

        self.alloc_urb(1)

        # Spend most of the time here
        # URBs will be recycled until no longer needed
        while self.urb_remain:
            self.running = self.running and len(self.completions) < self.n
            elapsed = int(time.time() - tstart) * 1000
            if elapsed >= timeout_ms:
                raise Exception("timeout after %s" % elapsed)
            # Pre-maturely allocating seems to cause issue
            if self.running and self.state == MSG_BEGIN:
                self.alloc_urb(self.urb_max - self.urb_remain)

            self.usbcontext.handleEventsTimeout(tv=0.1)

        for trans in self.trans_l:
            trans.close()
        
        # TODO: generate during process
        for completion in self.completions:
            yield completion


def cap_imgn(dev, usbcontext, n=1, timeout_ms=2500, verbose=1):
    cap = CapImgN(dev, usbcontext, n=n, verbose=verbose)
    try:
        for v in cap.run(timeout_ms=timeout_ms):
            yield v
    finally:
        cap.running = False


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

def unpack16(buff):
    return struct.unpack('>H', buff)[0]

def unpack16_le(buff):
    return struct.unpack('<H', buff)[0]

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


def open_dev(usbcontext=None, verbose=False):
    if usbcontext is None:
        usbcontext = usb1.USBContext()
    
    verbose and print('Scanning for devices...')
    for udev in usbcontext.getDeviceList(skip_on_error=True):
        vid = udev.getVendorID()
        pid = udev.getProductID()
        if (vid, pid) in ((HAM_VID, DC5_PID), (HAM_VID, DC12_PID)):
            if verbose:
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

"""
High level API object
"""

class Hamamatsu:
    def __init__(self, exp_ms=250, init=True):
        self.usbcontext = usb1.USBContext()
        self.dev = open_dev(self.usbcontext)
        self.dev.claimInterface(0)
        self.dev.resetDevice()
        self.exp_ms = exp_ms
        if init:
            ham_init(self.dev, exp_ms=self.exp_ms)
        self.debug = 0

    def cap(self, cb, n=1):
        raws=[]
        print("Collecting")
        for rawi, (counter, rawimg, _average) in enumerate(cap_imgn(self.dev, self.usbcontext, timeout_ms=(n * self.exp_ms + 5000), n=n)):
            print("img %u" % rawi)
            raws.append(rawimg)
        print("Dispatching")
        for i in range(n):
            print("img %u" % i)
            raw = raws[i]
            # very slow
            #if self.debug:
            #    assert check_sync(raw), "Found sync word in image data"
            cb(i, raw)
        print("exp: %u" % get_exp(self.dev))

    def set_exp(self, ms):
        self.exp_ms = ms
        set_exp(self.dev, ms)

    def get_vendor(self):
        return parse_info(get_info(self.dev))[0]
    
    def get_model(self):
        return parse_info(get_info(self.dev))[1]
    
    def get_ver(self):
        return parse_info(get_info(self.dev))[2]
    
    def get_sn(self):
        return parse_info(get_info(self.dev))[3]
