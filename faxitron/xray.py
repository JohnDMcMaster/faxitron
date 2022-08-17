"""
TODO: is there a model number?

Based on:
https://drive.google.com/file/d/1B64hYU_ONAPGTqL9EOMzYeRxt9jN4Q0G/view
Faxitron Documents/Faxitron Serial Commands MX-20 and DX-50.txt
Wonder where those came from?
"""

from faxitron import util
import serial
import time
import os


class Timeout(Exception):
    pass


class DoorOpen(Exception):
    pass


class WarmingUp(Exception):
    pass


def default_port():
    return "/dev/ttyUSB0"


# TODO: look into MX-20
class XRay:
    def __init__(self, port="/dev/ttyUSB0", ser_timeout=0.1, verbose=False):
        self.verbose = verbose
        self.verbose and print("opening", port)
        self.serial = serial.Serial(
            port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
            timeout=ser_timeout,
            # Blocking writes
            writeTimeout=None)
        self.serial.flushInput()
        self.serial.flushOutput()
        # Abort current command, if any
        #self.send("A")
        self.flush()

    def flush(self):
        """
        Wait to see if there is anything in progress
        """
        timeout = self.serial.timeout
        try:
            self.serial.timeout = 0.1
            while True:
                c = self.serial.read()
                if not c:
                    return
        finally:
            self.serial.timeout = timeout

    def recv_nl(self, timeout=1.0):
        """
        Most but not all commands respond with a new line
        """
        ret = ''
        tstart = time.time()
        while True:
            c = self.serial.read(1)
            if not c:
                if timeout is not None and time.time() - tstart >= timeout:
                    raise Timeout('Timed out')
                continue
            if c == b'\xFF':
                print("WARNING: bad response 0xFF")
                continue
            c = c.decode("ascii")
            self.verbose and print("%s %02X" % (c, ord(c)))
            if c == '\r':
                break
            ret += c
        else:
            raise Timeout('Timed out waiting for closing ~')

        if self.verbose:
            print('XRAY DEBUG: recv: returning: "%s"' % (ret, ))
        return ret

    def recv_c(self, timeout=1.0):
        tstart = time.time()
        while True:
            c = self.serial.read(1)
            if not c:
                if timeout is not None and time.time() - tstart >= timeout:
                    raise Timeout('Timed out')
                continue
            else:
                c = c.decode("ascii")
                self.verbose and print('XRAY DEBUG: recv: returning: %s %02X' %
                                       (c, ord(c)))
                return c

    def send(self, out, recv=False):
        """
        TODO: "The DX-50 will occasionally miss commands and queries, continue sending the string until the unit responds"
        Maybe add some retry logic
        """

        if self.verbose:
            print('XRAY DEBUG: sending: %s' % (out, ))
            if self.serial.inWaiting():
                raise Exception('At send %d chars waiting' %
                                self.serial.inWaiting())
        # \n seems to have no effect
        self.serial.write((out + '\r').encode('ascii'))
        self.serial.flush()
        if recv:
            ret = self.recv_nl()
            out_echo = ret[0:len(out)]
            # print(out_echo, out)
            assert out_echo == out
            return ret[len(out):]

    def get_device(self):
        """
        Get device model

        mcmaster: MX-20
        But other models like MX-20 should use the same API
        """
        ret = self.send("?D", recv=True)
        # FIXME: MX-20 support
        assert ret in ("DX-50", "MX-20")
        return ret

    def get_revision(self):
        """
        Get firmware revision as float

        mcmaster: 2.2
        Seltzman: 4.2
        Wonder what the differences are?
        """
        vers = self.send("?R", recv=True)
        # Verify its a valid version
        # ? why was this commented out
        float(vers)
        # But return as string to avoid precision issues
        return vers

    def assert_ready(self):
        s = self.get_state()
        if s == 'R':
            return
        elif s == 'D':
            raise DoorOpen()
        elif s == 'W':
            raise WarmingUp()
        else:
            assert 0

    def get_state(self):
        """
        Get overal device state
        W: warming up
        D: door open
        R: ready (door closed)
        """
        ret = self.send("?S", recv=True)
        assert ret in "WDR"
        return ret

    def get_mode(self):
        """
        Return one of:
        F: front panel
        R: remote
        """
        ret = self.send("?M", recv=True)
        assert ret in "FR"
        return ret

    def mode_remote(self):
        """
        Set mode to remote
        """
        self.send("!MR")
        # time.sleep(2.0)
        # No feedback, so query to verify set
        got = self.get_mode()
        assert got == "R", got

    '''
    def mode_panel(self):
        """
        Set mode to front panel
        """
        assert 0, "FIXME: doesn't seem to work"
        self.send("!MF")
        # time.sleep(2.0)
        # No feedback, so query to verify set
        got = self.get_mode()
        assert got == "F", got
    '''

    def set_kvp(self, n):
        """
        Set kV
        n: 10 - 35

        NOTE: beep
        """
        assert 10 <= n <= 35
        self.send("!V%u" % n)
        # No feedback, so query to verify set
        got = self.get_kvp()
        assert got == n, got

    def get_kvp(self):
        """
        ?V    Get kV.
        Reply ?V26
    """
        ret = self.send("?V", recv=True)
        ret = int(ret, 10)
        assert 10 <= ret <= 35
        return ret

    def get_timed(self):
        """
        Return exposure time in deciseconds
        """
        ret = self.send("?T", recv=True)
        ret = int(ret, 10)
        # FIXME: range?
        assert 1 <= ret <= 9999
        return ret

    def get_time(self):
        """
        Return exposure time in seconds
        """
        return self.get_timed() / 10.0

    def set_timed(self, dsec):
        """
        Set how long the tube will be on
        dsec: deciseconds (ie 10 => 1.0 sec)

        NOTE: beep
        """
        assert 1 <= dsec <= 9999
        self.send("!T%04u" % dsec)
        assert dsec == self.get_timed()

    def set_time(self, sec):
        """
        Set how long the tube will be on in seconds
        Rounded to nearest 10th second
        NOTE: beep
        """
        self.set_timed(round(sec * 10.0))

    def fire_begin(self, timeout=None, verbose=False):
        """
        NOTE: radiation emission

        WARNING: correct x-ray is not guaranteed
        I tried opening the door and it doesn't seem to do anything different
        ie it cut the exposure time and returned S as if completed normally

        TODO: add abort Lock based param?
        not needed for now
        """
        fire_time = self.get_time()
        kvp = self.get_kvp()
        if timeout is None:
            timeout = fire_time + 1.0
        verbose = verbose or self.verbose

        # Sanity check the door to avoid timeout below if possible
        self.assert_ready()

        try:
            # If the door is open, no response is given
            verbose and print("fire: starting, %0.1f s @ %s kVp" %
                              (fire_time, kvp))
            # Start x-ray sequence
            self.send("!B")
            # Wait for X to acknowledge firing (no newline)
            c = self.recv_c()
            assert c == "X", "Got '%s'" % c

            verbose and print("fire: confirming")
            # Confirm x-ray
            self.send("C")
            c = self.recv_c()
            assert c == "P"
        # notably ^C can cause this
        except:
            verbose and print("fire: aborting")
            self.send("A")

    def fire(self, timeout=None, verbose=False):
        self.fire_begin(timeout=timeout, verbose=verbose)

        try:
            verbose and print("fire: waiting")
            # Wait for x-ray to complete
            c = self.recv_c(timeout=timeout)
            assert c == "S"

            # Sanity check the door in case it was opened to interrupt the x-ray
            self.assert_ready()
        # notably ^C can cause this
        except:
            verbose and print("fire: aborting")
            self.send("A")

        verbose and print("fire: done")

    def fire_abort(self, verbose=False):
        verbose and print("fire: aborting")
        self.send("A")

    def get_json(self):
        return {
            "dev": self.get_device(),
            "rev": self.get_revision(),
            "mode": self.get_mode(),
            "state": self.get_state(),
            "timed": self.get_timed(),
            "kvp": self.get_kvp(),
        }

    def write_json(self, outdir):
        util.json_write(os.path.join(outdir, "source.json"), self.get_json())
