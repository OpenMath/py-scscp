from pexpect import fdpexpect, TIMEOUT, EOF
from .scscp import ProcessingInstruction as PI, PI_regex, SCSCPError

class SCSCPClient():
    INITIALIZED=0
    CONNECTED=1
    CLOSED=2

    def __init__(self, socket, timeout=30, logfile=None):
        self.socket = socket
        self.stream = fdpexpect.fdspawn(socket.makefile(), timeout=timeout, logfile=logfile)
        self.status = self.INITIALIZED

    def _get_next_PI(self, timeout=-1):
        try:
            self.stream.expect(PI_regex, timeout=timeout)
        except TIMEOUT:
            self.quit()
            raise TimeoutError("Server took to long to respond.")
        except EOF:
            raise ConnectionResetError("Server closed unexpectedly.")

        try:
            return PI.parse(self.stream.after)
        except SCSCPError:
            self.quit()
            raise

    def _send_PI(self, key='', **kwds):
        return self.socket.send(bytes(PI(key, **kwds)))
        
    def connect(self):
        if self.status > self.INITIALIZED:
            raise RuntimeError("Session already opened.")
        
        pi = self._get_next_PI()
        if pi.key:
            self.quit()
            raise SCSCPError("Server failed to initiate connection.")
        if ('scscp_versions' not in pi.attrs
                or b'1.3' not in pi.attrs['scscp_versions'].split()):
            self.quit()
            raise SCSCPError("Unsupported SCSCP versions %s." % pi.attrs.get('scscp_versions'))
        
        self.service_info = pi.attrs

        self._send_PI(version=b'1.3')

        pi = self._get_next_PI()
        if pi.key == 'quit':
            self.quit()
            raise SCSCPError("Server closed connection (reason: %s)." % pi.attrs.get('reason'))
        if pi.key or pi.attrs.get('version') != b'1.3':
            self.quit()
            raise SCSCPError("Server sent unexpected response.")

        self.connected = True

    def quit(self):
        self._send_PI('quit')
        self.socket.close()
        self.status = self.CLOSED
