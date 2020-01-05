from faxitron.util import add_bool_arg
from faxitron import ham

import json
import binascii
import subprocess
import os
import sys
import struct

'''
    (
    "\x08\x84\xA4\x06\x02\x00\x26\x00\x43\x00\xC0\x03\x00\x08\x10\x24"
    "\x00\x00\xC0\x1E\x00\x00\x85\x00")
'''
def str2hex(buff, prefix='', terse=True):
    if len(buff) == 0:
        return 'b""'
    buff = bytearray(buff)
    ret = ''
    if terse and len(buff) > 16:
        ret += '\n'
    for i in range(len(buff)):
        if i % 16 == 0:
            if i != 0:
                ret += '" \\\n'
            if len(buff) <= 16:
                ret += 'b"'
            if not terse or len(buff) > 16:
                ret += '%s"' % prefix
            
        ret += "\\x%02X" % (buff[i],)
    return ret + '"'

def str2hexline(buff):
    if len(buff) == 0:
        return '""'
    buff = bytearray(buff)
    ret = ''
    for i in range(len(buff)):
        ret += "\\x%02X" % (buff[i],)
    return '"' + ret + '"'

pi = None
ps = None

fout = sys.stdout

prefix = ' ' * 8
indent = ''
line_buff = []
def lines_clear():
    del line_buff[:]
def lines_commit():
    for line in line_buff:
        fout.write(line + '\n')
    del line_buff[:]
def line(s):
    line_buff.append('%s%s' % (indent, s))
def comment(s):
    line("# " + s)
def indentP():
    global indent
    indent += '    '
def indentN():
    global indent
    indent = indent[4:]

dumb = False
omit_ro = True

def emit_ro():
    '''Return true if keeping ro. Otherwise clear line buffer and return false'''
    if omit_ro:
        lines_clear()
        return False
    else:
        return False

def bin2hexarg(data):
    ret = str2hex(data, prefix=prefix)
    if len(data) > 16:
        ret += '\n%s' % prefix
    return ret

def pkt_strip(p):
    pprefix = ord(p[0])
    '''
    if pprefix != 0x08:
        #raise Exception("Bad prefix")
        line('# WARNING: unexpected prefix')
    '''
    size = (ord(p[-1]) << 8) | ord(p[-2])
    # Exact match
    if size == len(p) - 3:
        return (p[1:-2], False, pprefix)
    # Extra data
    # So far this is always 0 (should verify?)
    elif size < len(p) - 3:
        # TODO: verify 0 padding
        return (p[1:1 + size], True, pprefix)
    # Not supposed to happen
    else:
        print(bin2hexarg(p))
        print(size)
        raise Exception("Bad size")

class CmpFail(Exception):
    pass

def cmp_buff(exp, act):
    if len(exp) != len(act):
        raise CmpFail("Exp: %d, act: %d" % (len(exp), len(act)))

def cmp_mask(exp, mask, act):
    if len(exp) != len(act):
        hexdump(exp, indent='  ', label='expected')
        hexdump(act, indent='  ', label='actual')
        raise CmpFail("Exp: %d, act: %d" % (len(exp), len(act)))
    if len(exp) != len(mask):
        hexdump(exp, indent='  ', label='expected')
        hexdump(act, indent='  ', label='mask')
        raise CmpFail("Exp: %d, mask: %d" % (len(exp), len(mask)))
    for expc, actc in zip(exp, act):
        if mask == '\xFF' and expc != actc:
            hexdump(exp, indent='  ', label='expected')
            hexdump(act, indent='  ', label='actual')
            raise CmpFail("Exp: 0x%02X, act: 0x%02X" % (ord(exp), ord(actc)))

def peekp():
    return nextp()[1]

class OutOfPackets(Exception):
    pass

def nextp():
    ppi = pi + 1
    while True:
        if ppi >= len(ps):
            raise OutOfPackets("Out of packets, started packet %d, at %d" % (pi, ppi))
        p = ps[ppi]
        if p['type'] != 'comment':
            return ppi, p
        ppi = ppi + 1

def next_bulk1(cmd):
    global pi

    pi, pw = nextp()
    assert pw['type'] == 'bulkWrite', pw['type']
    assert pw['endp'] == 0x01
    assert binascii.unhexlify(pw['data']) == cmd

    pi, pr = nextp()
    assert pr['type'] == 'bulkRead'
    assert pr['endp'] == 0x83
    return binascii.unhexlify(pr['data'])

def pack32ub(n):
    return struct.pack('>I', n)

def pack32ul(n):
    return struct.pack('<I', n)

def pack16ub(n):
    return struct.pack('>H', n)

def pack16ul(n):
    return struct.pack('<H', n)

def unpack32ub(buff):
    return struct.unpack('>I', buff)[0]

def unpack32ul(buff):
    return struct.unpack('<I', buff)[0]

def unpack16ub(buff):
    return struct.unpack('>H', buff)[0]

def unpack16ul(buff):
    return struct.unpack('<H', buff)[0]

def bulk_write(pw):
    global pi

    '''
    Convert
    # Generated from packet 209/210
    bulkWrite(0x01, "\x00\x00\x00\x00\x00\x00\x00\x00")
    # Generated from packet 211/212
    buff = bulkRead(0x83, 0x0200)
    validate_read("\x01", buff, "packet 211/212")

    To use library function bulk1
    validate_read("\x01", bulk1(dev, "\x00\x00\x00\x00\x00\x00\x00\x00"), "packet 211/212")
    '''

    def basic_write():
        cmd = binascii.unhexlify(pw['data'])
        line('bulkWrite(0x%02X, %s)' % (pw['endp'], bin2hexarg(cmd)))

    if pw['endp'] != 0x01:
        comment("WARNING: unexpected write endpoint")
        basic_write()
        return

    pwdata = binascii.unhexlify(pw['data'])
    opcode, length = struct.unpack(">II", pwdata[0:8])
    payload = pwdata[8:]
    assert len(payload) == length

    if opcode == 0x0F:
        assert len(payload) == 0
        line("abort_stream(dev)")
        return

    pi_next, pr = nextp()
    assert pr['type'] == 'bulkRead'
    if pr['endp'] != 0x83:
        comment("WARNING: unexpected read endpoint")
        basic_write()
        return
    pi = pi_next

    prdata = binascii.unhexlify(pr['data'])


    # opcode 0 is known, but its boring
    if opcode == 1:
        assert length == 0
        # line("response = %s" % str2hex(prdata, prefix="        "))
        vendor, model, ver, sn = ham.parse_info1(prdata)
        comment("%s, %s, %s, %s" % (vendor, model, ver, sn))
        line("vendor, model, ver, sn = get_info1(dev)")
    elif opcode == 2:
        assert length == 0
        width, height = ham.parse_info2(prdata)
        comment("0x%04X, 0x%04X" % (width, height))
        line("width, height = get_info2(dev)")
    elif opcode == 4:
        assert length == 0
        width, height = struct.unpack('>II', prdata)
        comment("0x%04X, 0x%04X" % (width, height))
        line("width, height = get_roi_wh(dev)")
    elif opcode == 9:
        assert prdata == b"\x01"
        prefix = "\x00\x01\x00\x00\x00\x00"
        width, height = struct.unpack(">HH", payload[len(prefix):])
        line("set_roi_wh(dev, 0x%04X, 0x%04X)" % (width, height))
    elif opcode == 0x2D:
        assert prdata == b"\x00"
        op = struct.unpack(">H", payload)[0]
        if op == 1:
            line("trig_int(dev)")
        elif op == 5:
            line("trig_sync(dev)")
        else:
            line("trig_n(dev, %u)" % op)
    elif opcode == 0x1F:
        exp = unpack32ub(prdata)
        comment("%u ms" % exp)
        line("exposure = get_exp(dev)")
    elif opcode == 0x20:
        assert prdata == b"\x01"
        exp = unpack32ub(payload)
        line("set_exp_setup(dev, %u)" % exp)
        # XXX: there is a verify after this we should ideally eat
    elif opcode == 0x0E:
        assert payload == b"\x01"
        assert prdata == b"\x01"
        line("cap_begin(dev)")
    else:
        pktl, pkth = pw['packn']
        assert_msg = '"packet %u/%u"' % (pktl, pkth)
        response = bin2hexarg(prdata)
    
        # line('validate_read(%s, bulk1(dev, %s), %s)' % (response, out, desc))
        payload_arg = ""
        if len(payload):
            out = bin2hexarg(payload)
            payload_arg = ", payload=%s" % out
        line("validate_cmd1(dev, 0x%02X, %s, msg=%s%s)" % (opcode, response, assert_msg, payload_arg))


def dump(fin, source_str, save=False):
    global pi
    global ps

    comment("Generated from %s" % source_str)
    j = json.load(open(fin))
    pi = 0
    ps = j['data']
    ps = list(filter(lambda p: p['type'] != 'comment', ps))

    def eat_packet(type=None, req=None, val=None, ind=None, length=None):
        p = ps[pi + 1]

        if type and type != p['type']:
            raise Exception()
        if req and type != p['req']:
            raise Exception()
        if val and type != p['val']:
            raise Exception()
        if ind and type != p['ind']:
            raise Exception()
        if length and length != p['len']:
            raise Exception()
            
        return pi + 1

    im_bytes = None
    while pi < len(ps):
        is_comment = False
        p = ps[pi]
        if p['type'] == 'comment':
            line('# %s' % p['v'])
            is_comment = True
        elif p['type'] == 'bulkWrite':
            bulk_write(p)
        elif p['type'] == 'bulkRead':
            # print("# WARNING: dropping bulkRead")
            endpoint = p['endp']
            if endpoint == 0x82:
                buff = binascii.unhexlify(p["data"])
                sync_word = ham.is_sync(buff, verbose=False)
                if sync_word:
                    if sync_word == ham.MSG_BEGIN:
                        im_bytes = 0
                    elif sync_word == ham.MSG_END:
                        comment("Final bytes: %u" % im_bytes)
                        im_bytes = None
                    sync_str = ham.sync2str(sync_word)
                else:
                    sync_str = "NONE"
                    im_bytes += len(buff)
                comment("bulkRead(0x82): req %u, got %u bytes w/ sync %s" % (p['len'], len(buff), sync_str))
            else:
                comment("bulkRead(0x%02X): req %u, got %u bytes w/ sync %s" % (endpoint, p['len'], len(buff), sync_str))
        else:
            raise Exception("%u unknown type: %s" % (pi, p['type']))
        if not is_comment:
            lines_commit()
        pi += 1

    lines_commit()
    indentN()
    lines_commit()

if __name__ == "__main__":
    import argparse 
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--dumb', action='store_true')
    add_bool_arg(parser, '--omit-ro', default=True, help='Omit read only requests (ex: get SM info)')
    parser.add_argument('--big-thresh', type=int, default=255)
    parser.add_argument('--usbrply', default='')
    parser.add_argument('-w', action='store_true', help='Write python file')
    parser.add_argument('fin')
    args = parser.parse_args()

    source_str = args.fin
    if args.fin.find('.cap') >= 0 or args.fin.find('.pcapng') >= 0 or args.fin.find('.pcap') >= 0:
        fin = '/tmp/scrape.json'
        cmd = 'usbrply --packet-numbers --no-setup --device-hi %s -j %s >%s' % (args.usbrply, args.fin, fin)
        try:
            subprocess.check_call(cmd, shell=True)
        except:
            print("Failed to process %s" % args.fin)
            raise
    else:
        fin = args.fin

    if args.w:
        filename, file_extension = os.path.splitext(args.fin)
        fnout = filename + '.py'
        print('Selected output file %s' % fnout)
        assert fnout != fin, fin
        fout = open(fnout, 'w')

    dumb=args.dumb
    omit_ro=args.omit_ro
    dump(fin, source_str)
