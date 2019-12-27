from bpmicro.util import str2hex, add_bool_arg

import json
import binascii
import subprocess
import os
import sys

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

def bulk_write(p):
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

    if p['endp'] != 0x01:
        cmd = binascii.unhexlify(p['data'])
        line('bulkWrite(0x%02X, %s)' % (p['endp'], bin2hexarg(cmd, p['packn'][0])))
        return

    pi, pp = nextp()
    assert pp['type'] == 'bulkRead'

    pktl, pkth = p['packn']
    desc = '"packet %u/%u"' % (pktl, pkth)
    out = bin2hexarg(binascii.unhexlify(p['data']))
    response = bin2hexarg(binascii.unhexlify(pp['data']))

    print('validate_read(%s, bulk1(dev, %s), %s)' % (response, out, desc))


def dump(fin, save=False):
    global pi
    global ps

    j = json.load(open(fin))
    pi = 0
    ps = j['data']
    ps = filter(lambda p: p['type'] != 'comment', ps)

    def eat_packet(type=None, req=None, val=None, ind=None, len=None):
        p = ps[pi + 1]

        if type and type != p['type']:
            raise Exception()
        if req and type != p['req']:
            raise Exception()
        if val and type != p['val']:
            raise Exception()
        if ind and type != p['ind']:
            raise Exception()
        if len and len != p['len']:
            raise Exception()
            
        return pi + 1

    while pi < len(ps):
        comment = False
        p = ps[pi]
        if p['type'] == 'comment':
            line('# %s' % p['v'])
            comment = True
        elif p['type'] == 'bulkWrite':
            bulk_write(p)
        else:
            raise Exception("%u unknown type: %s" % (pi, p['type']))
        if not comment:
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

    if args.fin.find('.cap') >= 0 or args.fin.find('.pcapng') >= 0 or args.fin.find('.pcap') >= 0:
        fin = '/tmp/scrape.json'
        cmd = 'usbrply --packet-numbers --no-setup --device-hi %s -j %s >%s' % (args.usbrply, args.fin, fin)
        subprocess.check_call(cmd, shell=True)
    else:
        fin = args.fin

    if args.w:
        filename, file_extension = os.path.splitext(args.fin)
        fnout = filename + '.py'
        print('Selected output file %s' % fnout)
        assert fnout != fin
        fout = open(fnout, 'w')

    dumb=args.dumb
    omit_ro=args.omit_ro
    dump(fin)
