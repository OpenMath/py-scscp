from .client import SCSCPPeer, _assert_status, INITIALIZED, CONNECTED

class SCSCPServerBase(SCSCPPeer):
    """
    A simple SCSCP synchronous server, with no understanding of OpenMath.
    """
    
    def __init__(self, socket, timeout=30, logger=None):
        super(SCSCPServerBase, self).__init__(socket, timeout, logger, me="Server", you="Client")

    @_assert_status(INITIALIZED, "Session already opened.")
    def accept(self):
        """ SCSCP handshake """
        self._send_PI(scscp_versions=b'1.3')
        
        pi = self._get_next_PI([''])
        if pi.attrs.get('version') != b'1.3':
            self.quit()
            raise SCSCPConnectionError("Client sent unexpected response.", pi)
        
        self._send_PI(version=b'1.3')

        self.status = CONNECTED
