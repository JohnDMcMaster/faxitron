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

    def get_mode(self):
        """
        Return one of:
        F: front panel
        R: remote
        """
        ret = self.send("?M", recv=True)
        assert ret in "FR"
        return ret

    def get_device(self):
        """
?D    Get device.
    Reply MX-20

        """
        ret = self.send("?D", recv=True)
        # FIXME: MX-20 support
        assert ret == "DX-50"
        return ret

    def get_revision(self):
        """
?R    Get revision.
    Reply 4.2
        """
        return float(self.send("?R", recv=True))

    def get_state(self):
        """
?S    Get state.
    Reply ?SW: Warming up
    Reply ?SD: Door open
    Reply ?SR: Ready

        """

    def mode_remote(self):
        """
        !MR    Set mode remote
        """
        self.send("!MR")
        # No feedback, so query to verify set
        assert self.get_mode() == "R"

    def mode_panel(self):
        """
!MF    Set mode front panel
        """
        self.send("!MF")
        # No feedback, so query to verify set
        assert self.get_mode() == "F"

    def set_kvp(self, n):
        """
!V26    Set kV (10-35)
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

    def set_expi(self, expi):
        """
!T0140    Set 14.0 sec exposure
    Range 0.1-999.9 (T0001-T9999)

        """
        self.send("?T%03u" % expi)
        assert expi == self.get_expi()

    def set_exp(self, exp):
        self.set_expi(round(exp * 10.0))

    def get_expi(self):
        """
        Return exposure time in 10th second

        Note: low level returns in 10ths of second
        Ex: reply T0140 => 14.0 sec
        """
        ret = self.send("?T", recv=True)
        ret = int(ret, 10)
        # FIXME: range?
        # assert 10 <= ret <= 35
        return ret

    def get_exp(self):
        return self.get_expi() * 10.0

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




