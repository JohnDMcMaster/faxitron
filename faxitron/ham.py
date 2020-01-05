#!/usr/bin/env python3

import binascii
import datetime
import time
import usb1
from faxitron.util import hexdump, add_bool_arg, tobytes, tostr
from PIL import Image
import os
import struct
import sys

HAM_VID = 0x0661
# C9730DK-11
DC5_PID = 0xA802
DC12_PID = 0xA800

# TODO: consider upshifting to make raw easier to see
PIX_MAX = 0x3FFF

MSG_ABORTED = 0x8001
# 32770
# Image start
# Payload: length: image size + 2
# XXX: DC12 has 4 byte payload? Double check this is correct
# DC12:
# 0040   04 80 0e 00 d3 d7
MSG_BEGIN = 0x8002
# Payload length: 2 bytes
# ex: value 3
MSG_END = 0x8004
"""
Getting this means that a new frame will come
I think it represents a real time failure

from official capture
"Lost frame"
# bulkRead(0x82): req 16384, got 1026 bytes w/ sync NONE, 1573890 bytes total
# bulkRead(0x82): req 3584, got 2 bytes w/ sync MSG_ERROR, 1573890 bytes total
# bulkRead(0x82): req 16384, got 2 bytes w/ sync MSG_BEGIN, 0 bytes total
# bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE, 16384 bytes total
...
# bulkRead(0x82): req 3584, got 3074 bytes w/ sync NONE, 11082242 bytes total
# Final bytes: 11082242
# bulkRead(0x82): req 512, got 6 bytes w/ sync MSG_END, None bytes total
# bulkRead(0x82): req 512, got 2 bytes w/ sync MSG_BEGIN, 0 bytes total
"""
MSG_ERROR = 0x8005
MSG_END_SZ = 6

STATUS_OK_DC5 = 0x03
# observed around same time saw MSG_ERROR
STATUS_NOK = 0x07
STATUS_OK_DC12 = 0x0E

def unpack32ub(buff):
    return struct.unpack('>I', buff)[0]

def unpack32ul(buff):
    return struct.unpack('<I', buff)[0]

def unpack16ub(buff):
    return struct.unpack('>H', buff)[0]

def unpack16ul(buff):
    return struct.unpack('<H', buff)[0]

def now():
    return datetime.datetime.utcnow().isoformat()

def validate_read(expected, actual, msg=""):
    expected = tobytes(expected)
    actual = tobytes(actual)
    if expected != actual:
        print('Failed %s' % msg)
        print('  Expected; %s' % binascii.hexlify(expected,))
        print('  Actual:   %s' % binascii.hexlify(actual,))
        raise Exception('failed validate: %s' % msg)

def bulk1(dev, cmd, read=True):
    def bulkWrite(endpoint, data, timeout=None):
        dev.bulkWrite(endpoint, tobytes(data), timeout=(1000 if timeout is None else timeout))

    def bulkRead(endpoint, length, timeout=None):
        ret = dev.bulkRead(endpoint, length, timeout=(1000 if timeout is None else timeout))
        if 0:
            print('')
            hexdump(ret, label='bulkRead(%u)' % length, indent='')
        return ret

    bulkWrite(0x01, cmd)
    if read:
        return bulkRead(0x83, 0x0200)

def cmd1(dev, opcode, payload=b"", read=True):
    buff = struct.pack(">II", opcode, len(payload))
    return bulk1(dev, buff + payload, read=read)


def validate_cmd1(dev, opcode, expected, payload=b"", msg=""):
    buff = cmd1(dev, opcode, payload=payload)
    #got = struct.unpack(">c", buff)[0]
    #assert expect == got, (msg, expect, got)
    validate_read(expected, buff, msg)

def force_trig(dev):
    validate_cmd1(dev, 0x0E, "\x01", payload=b"\x01", msg="force_trig")

def abort_stream(dev):
    # Special: seems to be the only thing that doesn't get a reply?
    # Usually these are followed by reply on 0x83, but instead it gets a reply on 0x83 as MSG_ABORTED
    cmd1(dev, 0x0F, read=False)

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

def parse_info1(buff):
    assert len(buff) == 0x80
    buff = tostr(buff)
    assert len(buff) == 0x80
    vendor = buff[0x00:0x20].replace('\x00', '')
    model = buff[0x20:0x40].replace('\x00', '')
    ver = buff[0x40:0x60].replace('\x00', '')
    sn = buff[0x60:0x80].replace('\x00', '')
    return vendor, model, ver, sn

def get_info1(dev):
    return parse_info1(cmd1(dev, 1))

def parse_info2(buff):
    def unpack16(b):
        return struct.unpack('>H', b)[0]
    validate_read(binascii.unhexlify("000000140000"), buff[0:6], "packet 217/218-0")
    width = unpack16(buff[6:8])
    validate_read(binascii.unhexlify("0000"), buff[8:10], "packet 217/218-8")
    height = unpack16(buff[10:12])
    validate_read(binascii.unhexlify("0000001000000001"), buff[12:], "packet 217/218-12")
    

    assert (width, height) in [(1032, 1032), (2368,2340 )], (width, height)

    return width, height

def get_info2(dev):
    """
    0x0408 (1032), 0x0940 (2368), 0x0924 (2340)

    DC5
    Expected; b'0000001400000408000004080000001000000001'
    DC12
    Actual:   b'0000001400000940000009240000001000000001'
    """
    buff = cmd1(dev, 2)
    return parse_info2(buff)

def set_roi_wh(dev, width, height):
    payload = b"\x00\x01\x00\x00\x00\x00" + struct.pack('>HH', width, height)
    validate_read(b"\x01", cmd1(dev, 9, payload=payload), msg="set_roi_wh")

def get_roi_wh(dev):
    # DC5
    # validate_read(b"\x00\x00\x04\x08\x00\x00\x04\x08", 
    buff = cmd1(dev, 4)
    return struct.unpack('>II', buff)


def ham_init(dev, exp_ms=500):
    """
    Generated from ./dc5/2019-12-26_02_init.pcapng
    Augmented from ./dc12/2020-01-04_01_dc12_init_snap.pcapng
    
    Other:
    DC5 seems to have default exposure 250 ms, but DC12 is 1000 ms
    """

    validate_cmd1(dev, 0x00, "\x01", msg="packet 209/210")
    # HAMAMATSU, C9730DK-11, 1.21, 5403219
    vendor, model, ver, sn = get_info1(dev)
    # 0x0408, 0x0408
    width_ret, height_ret = get_info2(dev)
    validate_cmd1(dev, 0x24, b"\x00\x00\x00\x06\x00\x00\x00\x20\x00\x00\x00\x03", msg="packet 221/222")
    validate_cmd1(dev, 0x2A, b"\x00", msg="packet 225/226")
    validate_cmd1(dev, 0x39, b"\x00", msg="packet 229/230")
    validate_cmd1(dev, 0x3A, b"\x00", msg="packet 233/234")
    validate_cmd1(dev, 0x3B, b"\x00", msg="packet 237/238")
    validate_cmd1(dev, 0x3C, b"\x00", msg="packet 241/242")
    validate_cmd1(dev, 0x3D, b"\x00", msg="packet 245/246")
    validate_cmd1(dev, 0x4A, b"\x00", msg="packet 249/250")
    validate_cmd1(dev, 0x4F, b"\x00", msg="packet 253/254")
    validate_cmd1(dev, 0x23, b"\x01", msg="packet 257/258")
    validate_cmd1(dev, 0x29, b"\x00", msg="packet 261/262")
    # HAMAMATSU, C9730DK-11, 1.21, 5403219
    vendor, model, ver, sn = get_info1(dev)
    # HAMAMATSU, C9730DK-11, 1.21, 5403219
    vendor, model, ver, sn = get_info1(dev)
    # HAMAMATSU, C9730DK-11, 1.21, 5403219
    vendor, model, ver, sn = get_info1(dev)
    set_roi_wh(dev, width_ret, height_ret)
    # 0x0408, 0x0408
    width, height = get_roi_wh(dev)
    assert (width, height) == (width_ret, height_ret), (width, height, width_ret, height_ret)
    validate_cmd1(dev, 0x2E, b"\x00", msg="packet 285/286", payload=b"\x00\x00\x00\x02")
    validate_cmd1(dev, 0x2E, b"\x00", msg="packet 289/290", payload=b"\x00\x00\x00\x12")
    validate_cmd1(dev, 0x2E, b"\x00", msg="packet 293/294", payload=b"\x00\x00\x00\x18")
    validate_cmd1(dev, 0x21, b"\x3F\x9E\xB8\x51\xEB\x85\x1E\xB8", msg="packet 297/298", payload=b"\x00\x00\x00\x00")
    validate_cmd1(dev, 0x21, b"\x40\x34\x00\x00\x00\x00\x00\x00", msg="packet 301/302", payload=b"\x00\x00\x00\x01")
    validate_cmd1(dev, 0x21, b"\x3F\x50\x62\x4D\xD2\xF1\xA9\xFC", msg="packet 305/306", payload=b"\x00\x00\x00\x02")
    validate_cmd1(dev, 0x21, b"\x00\x00\x00\x00\x00\x00\x00\x00", msg="packet 309/310", payload=b"\x00\x00\x00\x03")
    set_exp(dev, 2000)
    # 2000 ms
    exposure = get_exp(dev)
    set_exp(dev, 1000)
    # 250 ms
    exposure = get_exp(dev)
    set_exp(dev, 1000)
    # 250 ms
    exposure = get_exp(dev)
    trig_int(dev)
    # 250 ms
    exposure = get_exp(dev)
    validate_cmd1(dev, 0x2E, b"\x00", msg="packet 345/346", payload=b"\x00\x00\x00\x12")
    validate_cmd1(dev, 0x2E, b"\x00", msg="packet 349/350", payload=b"\x00\x00\x00\x02")
    set_exp(dev, 1000)
    # 250 ms
    exposure = get_exp(dev)
    trig_int(dev)
    return width_ret, height_ret

def check_sync(buff, verbose=True):
    syncpos = 0
    n = 0
    while len(buff):
        #if len(buff) % 1000 == 0:
        #    print(len(buff))
        pack2u = unpack16_le(buff[0:2])
        if pack2u >= 0x4000:
            verbose and print("MSG 0x%04X @ 0x%04X, %u bytes => %s" % (pack2u, syncpos, len(buff), binascii.hexlify(buff[0:16])))
            #hexdump(buff[0:16], "Sync found")
            n += 1
        buff = buff[2:]
        syncpos += 2

    return n

def is_sync(buff, verbose=True):
    if len(buff) == 0:
        return 0
    pix0 = unpack16ul(buff[0:2])
    # proper check is probably & 0x8000
    # but anything in this range is not valid pixel
    if pix0 >= 0x4000:
        verbose and print("MSG 0x%04X (%s), %u bytes => %s" % (pix0, sync2str(pix0), len(buff), binascii.hexlify(buff[0:16])))
        #hexdump(buff[0:16], "Sync found")
        return pix0
    else:
        return 0

def sync2str(word):
    return {
        MSG_ABORTED: "MSG_ABORTED",
        MSG_BEGIN: "MSG_BEGIN",
        MSG_END: "MSG_END",
        MSG_ERROR: "MSG_ERROR",
        }.get(word, "MSG_%04X" % word)

# TODO: make this thread capable to always take images and suck off as needed
#STATE_BEGIN = 'BEGIN'
#STATE_END = 'END'
class CapImgN:
    def __init__(self, dev, usbcontext, width, height, depth=2, n=1, verbose=1):
        self.dev = dev
        self.usbcontext = usbcontext
        self.verbose = verbose
        self.width = width
        self.widthd = width * depth
        self.height = height
        self.heightd = height * depth
        self.depth = depth
        assert (width, height) == (2368, 2340), "FIXME DC12 temp"
        self.imgsz = width * height * depth
        self.n = n
        #self.state = STATE_END
        self.urb_remain = 0
        self.lost_frames = 0
        """
        33 outstanding URBs at any time?
        This is the repeating sequence (DC5, DC12)
        Additionally BEGIN/END are 512 instead of 16384

        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 3584, got 3584 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 16384, got 16384 bytes w/ sync NONE
        # bulkRead(0x82): req 12800, got 12800 bytes w/ sync NONE

        """
        self.urb_size = 0x4000

        # len(self.rawbuff) < imgx_sz and len(self.messages) < 1
        self.rawbuff = None
        self.urb_max = 31

        # for debugging
        self.packets = 0
        self.running = True


        self.MSG_BEGIN_SZ = 2 + self.imgsz
        # Including average after
        self.imgx_sz = self.imgsz + 2
        self.lens = []

    def process_end(self, endbuff):
        self.verbose and print("rawbuff: %u bytes" % len(self.rawbuff))
        buff = self.rawbuff[0:self.imgx_sz]
        self.verbose and print("buff: %u bytes" % len(buff))
        rawimg = buff[0:self.imgsz]
        self.verbose and print("rawimg: %u bytes" % len(rawimg))
        footer = buff[self.imgsz:]
        self.verbose and print("footer: %u bytes" % len(footer))

        for i, l in enumerate(self.lens):
            print("%u %u" % (i, l))

        if self.verbose:
            hexdump(buff[self.widthd*0:self.widthd*0+16], "First row")
            hexdump(buff[self.widthd*1:self.widthd*1+16], "Second row")
            hexdump(buff[self.widthd*(self.width - 1):self.widthd*(self.width-1)+16], "Last row")
            hexdump(buff[-16:], "Last bytes")
            hexdump(footer, "Image footer")
            #hexdump(rawbuff, "Additional bytes")
            print("Additional bytes: %u" % len(self.rawbuff))
            assert len(self.rawbuff) == self.imgx_sz, "%u bytes, overshot by %u bytes" % (len(self.rawbuff), len(self.rawbuff) - self.imgx_sz)
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
        assert opcode == MSG_END, opcode
        status, counter = struct.unpack('<HH', endbuff[2:])
        print("Status: %u, counter: %u" % (status, counter))
        if not status in (STATUS_OK_DC5, STATUS_OK_DC12):
            print("WARNING: bad status %u. Discarding frame" % status)
            return
        
        assert len(rawimg) == self.imgsz, (len(rawimg), self.imgsz)

        return counter, rawimg, average

    def async_cb(self, trans):
        try:
            self.urb_remain -= 1
            self.packets += 1
            if not self.running:
                return

            # f you API. Why would anyone want uninitialized memory?
            buff = trans.getBuffer()[:trans.getActualLength()]
            sync = is_sync(buff)
            if sync:
                net_bytes = 0 if self.rawbuff is None else len(self.rawbuff)
                # Don't warn after recovering from error
                if not (self.rawbuff is None and sync == MSG_BEGIN):
                    print("WARNING: expected data, got %s, %u packets w/ %u frame bytes" % (sync2str(sync), self.packets, net_bytes))
                trans.submit()
                self.urb_remain += 1
                self.rawbuff = None
            else:
                # In particular this can happen for a bit after MSG_ERROR
                if self.rawbuff is None:
                    trans.submit()
                    self.urb_remain += 1
                    return

                assert len(self.rawbuff) < self.imgx_sz, len(self.rawbuff)
                assert not sync, ("0x%04X" % sync, len(self.rawbuff))
                self.lens.append(len(buff))

                self.rawbuff.extend(buff)
        
                est_submit = len(self.rawbuff) + self.urb_size * self.urb_remain
                est_remain = self.imgx_sz - est_submit
    
                if est_remain > 0:
                    assert len(self.rawbuff) < self.imgx_sz
                    self.urb_remain += 1
                    trans.submit()
        except:
            self.running = False
            raise

    def alloc_urb(self):
        # reference only does 31, so stay with that
        for urbi in range(33):
            trans = self.dev.getTransfer()
            if 1:
                if urbi == 1:
                    urb_size = 3584
                elif urbi == 32:
                    urb_size = 12800
                else:
                    urb_size = self.urb_size
            else:
                urb_size = self.urb_size
            trans.setBulk(0x82, urb_size, callback=self.async_cb, user_data=None, timeout=2500)
            trans.submit()
            self.trans_l.append(trans)
            self.urb_remain += 1

    def run_cap(self):
        self.rawbuff = bytearray()
        self.packets = 0

        self.trans_l = []
        self.urb_remain = 0

        self.alloc_urb()

        # Spend most of the time here
        # URBs will be recycled until no longer needed
        while self.urb_remain:
            elapsed = int(time.time() - self.tstart) * 1000
            if elapsed >= self.timeout_ms:
                raise Exception("timeout after %s" % elapsed)

            self.usbcontext.handleEventsTimeout(tv=0.1)

        for trans in self.trans_l:
            trans.close()

        print("%u packets, %u bytes" % (self.packets, len(self.rawbuff)))
        assert self.running

    """
    Timing example
    23.218949:23.218971: submit begin request (bulkWrite 1)
    23.220151:24.048424: wait begin response (bulkRead 3)
        dt: 0.828273
    24.050377:25.050133: wait begin message (bulkRead 2)
        dt: 0.999756
    25.066560
        33 URBs submitted

    Is there a chance I'm going too quick between init and cap?
    """
    # TODO: reconsider error handling on bad messages
    def run(self, timeout_ms=2500):
        self.timeout_ms = timeout_ms
        try:
            self.tstart = time.time()
            for imgi in range(self.n):
                while True:
                    self.rawbuff = None
                    self.packets = None
                    self.lens = []
                    buff = self.dev.bulkRead(0x82, 512)
                    sync = is_sync(buff)
                    if sync != MSG_BEGIN:
                        print("WARNING: expected BEGIN, got sync %s" % sync2str(sync))
                        continue
                    
                    # time.slesyep(0.016)
    
                    print("run_cap() begin")
                    self.run_cap()
                    print("run_cap() end")
    
                    buff = self.dev.bulkRead(0x82, 512)
                    sync = is_sync(buff)
                    if sync != MSG_END:
                        print("WARNING: expected END, got sync %s" % sync2str(sync))
                        continue
    
                    yield self.process_end(buff)
                    self.rawbuff = None
                    break


            buff = self.dev.bulkRead(0x82, 512)
            sync = is_sync(buff)
            assert sync == MSG_BEGIN, sync2str(sync)

            abort_stream(self.dev)

            tabort = time.time()
            while time.time() - tabort < 1.0:
                buff = self.dev.bulkRead(0x82, 512)
                if is_sync(buff) == MSG_ABORTED:
                    break
            else:
                raise Exception("Failed to get abort")
        finally:
            self.running = False


def cap_imgn(dev, usbcontext, width, height, depth=2, n=1, timeout_ms=2500, verbose=1):
    cap = CapImgN(dev, usbcontext, width, height, depth=depth, n=n, verbose=verbose)
    try:
        for v in cap.run(timeout_ms=timeout_ms):
            yield v
    finally:
        cap.running = False


def decode(buff, width, height, depth=2):
    '''Given bin return PIL image object'''
    buff = bytearray(buff)
    assert len(buff) == width * height * depth

    # no need to reallocate each loop
    img = Image.new("I", (width, height), "White")

    for y in range(height):
        line0 = buff[y * width * depth:(y + 1) * width * depth]
        for x in range(width):
            b0 = line0[2*x + 0]
            b1 = line0[2*x + 1]
            img.putpixel((x, y), (b1 << 8) + b0)
    return img

def trig_n(dev, n):
    validate_cmd1(dev, 0x2D, "\x00", msg="trig_n()", payload=struct.pack(">H", n))

def trig_int(dev):
    trig_n(dev, 1)

def trig_sync(dev):
    trig_n(dev, 5)

def unpack16_le(buff):
    return struct.unpack('<H', buff)[0]

def get_exp(dev):
    def unpack32(buff):
        return struct.unpack('>I', buff)[0]

    return unpack32(cmd1(dev, 0x1F))

def set_exp(dev, exp_ms):
    # Determined experimentally
    # less than 30 verify fails
    # setting above 2000 seems to silently fail and peg at 2000
    # 3000 is slightly brighter than 2000 though, so the actual limit might be 2048 or something of that sort
    assert 30 <= exp_ms <= 2000

    def pack32(n):
        return struct.pack('>I', n)

    validate_cmd1(dev, 0x20, "\x01", payload=pack32(exp_ms), msg="set_exp")
    #assert get_exp(dev) == exp_ms


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
    def __init__(self, exp_ms=1000, init=True):
        self.usbcontext = usb1.USBContext()
        self.dev = open_dev(self.usbcontext)
        self.dev.claimInterface(0)
        self.dev.resetDevice()
        self.exp_ms = exp_ms

        self.width = None
        self.height = None
        self.depth = 2
        if init:
            self.width, self.height = ham_init(self.dev, exp_ms=self.exp_ms)

        self.debug = 0

    def cap(self, cb, n=1):
        time.sleep(3)

        # Generated from ./dc5/2019-12-26_02_init.pcapng
        dev = self.dev
        set_roi_wh(dev, self.width, self.height)
        # 0x0940, 0x0924
        width, height = get_roi_wh(dev)
        set_roi_wh(dev, self.width, self.height)
        # 0x0940, 0x0924
        width, height = get_roi_wh(dev)
        # 0x0940, 0x0924
        width, height = get_roi_wh(dev)
        force_trig(dev)




        raws=[]
        print("Collecting")
        """
        timeout
        Give allocation for one corrupt image...ocassionally happens at begin
        """
        for rawi, (counter, rawimg, _average) in enumerate(cap_imgn(self.dev, self.usbcontext, self.width, self.height, self.depth, timeout_ms=((n + 1) * (self.exp_ms + 250) + 1000), n=n)):
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
        return get_info1(self.dev)[0]
    
    def get_model(self):
        return get_info1(self.dev)[1]
    
    def get_ver(self):
        return get_info1(self.dev)[2]
    
    def get_sn(self):
        return get_info1(self.dev)[3]

    def decode(self, buff):
        return decode(buff, self.width, self.height)
