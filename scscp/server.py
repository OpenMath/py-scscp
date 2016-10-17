from .client import SCSCPPeer, SCSCPPeerOM, _assert_status, INITIALIZED, CONNECTED
from .scscp import SCSCPConnectionError, SCSCPProcedureMessage

class SCSCPServerBase(SCSCPPeer):
    """
    A simple SCSCP synchronous server, with no understanding of OpenMath.
    """
    
    def __init__(self, socket, timeout=30, logger=None):
        super(SCSCPServerBase, self).__init__(socket, timeout, logger, me="Server", you="Client")

    @_assert_status(INITIALIZED, "Session already opened.")
    def accept(self, timeout=None):
        """ SCSCP handshake """
        self._send_PI(scscp_versions=b'1.3')
        
        pi = self._get_next_PI([''], timeout=timeout)
        if pi.attrs.get('version') != b'1.3':
            self.quit()
            raise SCSCPConnectionError("Client sent unexpected response.", pi)
        
        self._send_PI(version=b'1.3')

        self.status = CONNECTED

        
class SCSCPServer(SCSCPServerBase, SCSCPPeerOM):
    """
    A simple SCSCP synchronous server.
    """
    def wait(self, timeout=-1):
        return SCSCPProcedureMessage.from_om(self.receive(timeout))

    def completed(self, id, data, **info):
        comp = SCSCPProcedureMessage.completed(id, data, **info)
        self.send(comp.om())
        return comp

    def terminated(self, id, error, msg=None, **info):
        term = SCSCPProcedureMessage.terminated(id, error, msg, **info)
        self.send(term.om())
        return term
