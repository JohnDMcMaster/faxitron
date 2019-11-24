"""
TODO: is there a model number?

Based on:
https://drive.google.com/file/d/1B64hYU_ONAPGTqL9EOMzYeRxt9jN4Q0G/view
Faxitron Documents/Faxitron Serial Commands MX-20 and DX-50.txt
Wonder where those came from?

Faxitron Serial Commands for MX-20 and DX-50
all commands <!xxxxx> must be followed by a <CR>, 'C' and 'A' do not require a <CR>
The DX-50 will occasionally miss commands and queries, continue sending the string until the unit responds
-------------------------

!MR    Set mode remote
!MR    Set mode front panel
!V26    Set kV (10-35)
!T0140    Set 14.0 sec exposure
    Range 0.1-999.9 (T0001-T9999)

!B    Initiates X-ray
    Then this sequence:
    Machines replies "X" X-ray
    Write "C" Continue to start actual X-ray
    Machines replies "P" Processing
    Write "A" to abort
    Machine replies "S" when complete

?S    Get state.
    Reply ?SW: Warming up
    Reply ?SD: Door open
    Reply ?SR: Ready

?M    Get mode.
    Reply ?MF: Front panel mode
    Reply ?MR: Remote mode

?D    Get device.
    Reply MX-20

?R    Get revision.
    Reply 4.2

?V    Get kV.
    Reply ?V26

?T    Get exposure time.
    Reply T0140


!V26


"""

import serial
import math

class Timeout:
    pass

class XRay:
    def __init__(self, port="/dev/ttyUSB0", ser_timeout=10.0, verbose=False):
        self.verbose = verbose
        self.serial = serial.Serial(port,
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
            self.serial.timeout = 0.05
            while True:
                c = self.serial.read()
                if not c:
                    return
        finally:
            self.serial.timeout = timeout

    def recv_nl(self):
        """
        Most but not all commands respond with a new line
        """
        # Read until ~
        ret = ''
        for _i in range(60):
            c = self.serial.read(1)
            if c is not None:
                c = c.decode("ascii")
                self.verbose and print("%s %02X" % (c, ord(c)))
            if c == '\r':
                break
            ret += c
        else:
            raise Timeout('Timed out waiting for closing ~')
        
        if self.verbose:
            print('XRAY DEBUG: recv: returning: "%s"' % (ret,))
        return ret

    def send(self, out, recv=False):
        if self.verbose:
            print('XRAY DEBUG: sending: %s' % (out,))
            if self.serial.inWaiting():
                raise Exception('At send %d chars waiting' % self.serial.inWaiting())
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
        assert ret == "DX-50"
        return ret

    def get_revision(self):
        """
        Get firmware revision as float

        mcmaster: 2.2
        Seltzman: 4.2
        Wonder what the differences are?
        """
        return float(self.send("?R", recv=True))

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
        # No feedback, so query to verify set
        assert self.get_mode() == "R"

    def mode_panel(self):
        """
        Set mode to front panel
        """
        self.send("!MF")
        # No feedback, so query to verify set
        assert self.get_mode() == "F"

    def set_kvp(self, n):
        """
        Set kV
        n: 10 - 35

        NOTE: beep
        """
        assert 10 <= n <= 35
        self.send("!V%u" % n)
        # No feedback, so query to verify set
        assert self.get_kvp() == n

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
        assert 1 <= ret <=  9999
        return ret

    def get_time(self):
        """
        Return exposure time in seconds
        """
        return self.get_timed() * 10.0

    def set_timed(self, dsec):
        """
        Set how long the tube will be on
        dsec: deciseconds (ie 10 => 1.0 sec)

        NOTE: beep
        """
        assert 1 <= dsec <=  9999
        self.send("!T%04u" % dsec)
        print(dsec, self.get_timed())
        assert dsec == self.get_timed()

    def set_time(self, sec):
        """
        Set how long the tube will be on in seconds
        Rounded to nearest 10th second
        NOTE: beep
        """
        self.set_timed(round(sec * 10.0))

    def fire(self):
        """
!B    Initiates X-ray
    Then this sequence:
    Machines replies "X" X-ray
    Write "C" Continue to start actual X-ray
    Machines replies "P" Processing
    Write "A" to abort
    Machine replies "S" when complete
        """
