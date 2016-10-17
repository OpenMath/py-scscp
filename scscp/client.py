import logging
from pexpect import fdpexpect, TIMEOUT, EOF
from openmath import encoder, decoder
from . import scscp
from .scscp import SCSCPConnectionError, SCSCPQuit, SCSCPCancel, SCSCPProcedureMessage
from .processing_instruction import ProcessingInstruction as PI

class TimeoutError(RuntimeError):
    """ Client/Server timeout """
    pass
    
INITIALIZED=0
CONNECTED=1
CLOSED=2

def _assert_status(status, msg=None):
    def wrap(fun):
        def wrapper(self, *args, **kwds):
            if self.status != status:
                raise RuntimeError(msg or "Bad status %d." % self.status)
            return fun(self, *args, **kwds)
        return wrapper
    return wrap
_assert_connected = _assert_status(CONNECTED, "Not connected.")


class SCSCPPeer(object):
    """
    Base class for SCSCP client and server
    """
    
    def __init__(self, socket, timeout=30, logger=None, me='Client', you='Server'):
        self.socket = socket
        self.stream = fdpexpect.fdspawn(socket, timeout=timeout)
        self.status = INITIALIZED
        self.log = logger or logging.getLogger(__name__)
        self.me, self.you = me, you

    def _get_next_PI(self, expect=None, timeout=-1):
        while True:
            try:
                self.stream.expect(PI.PI_regex, timeout=timeout)
            except TIMEOUT:
                raise TimeoutError("%s took too long to respond." % self.you)
            except EOF:
                raise ConnectionResetError("%s closed unexpectedly." % self.you)

            try:
                pi = PI.parse(self.stream.after)
            except SCSCPConnectionError:
                self.quit()
                raise
            self.log.debug("Received PI: %s" % pi)

            if expect is not None and pi.key not in expect:
                if pi.key == 'quit':
                    self.quit()
                    reason = pi.attrs.get('reason')
                    raise SCSCPQuit("%s closed session (reason: %s)." % (self.you, reason), reason)
                if pi.key == '' and 'info' in pi.attrs:
                    self.log.info("SCSCP info: %s" % pi.attrs.get('info').decode())
                    continue
                else:
                    raise SCSCPConnectionError("%s sent unexpected message: %s" % (self.you, pi.key), pi)
            else:
                return pi


    def _send_PI(self, key='', **kwds):
        pi = PI(key, **kwds)
        self.log.debug("Sending PI: %s" % pi)
        return self.socket.send(bytes(pi))

    @_assert_connected
    def send(self, msg):
        """ Send SCSCP message """
        self._send_PI('start')
        try:
            self.socket.send(msg)
        except:
            self._send_PI('cancel')
            raise
        else:
            self._send_PI('end')

    @_assert_connected
    def receive(self, timeout=-1):
        """ Receive SCSCP message """
        msg = b""
        pi = self._get_next_PI(['start'], timeout=timeout)
        while True:
            pi = self._get_next_PI(['end', 'cancel'], timeout=timeout)
            if pi.key == 'cancel':
                raise SCSCPCancel('%s canceled transmission' % self.you)
            
            msg += self.stream.before
            return msg

    @_assert_connected
    def quit(self, reason=None):
        """ Send SCSCP quit message """
        kwds = {} if reason is None else { 'reason': None }
        try:
            self._send_PI('quit', **kwds)
            self.socket.close()
        except ConnectionError:
            pass
        finally:
            self.status = CLOSED

    @_assert_connected
    def info(self, info):
        """ Send SCSCP info message """
        self._send_PI(info=info)


class SCSCPPeerOM(SCSCPPeer):
    """
    Base class for SCSCP client and server understanding OpenMath
    """
    
    def receive(self, timeout=-1):
        msg = super(SCSCPPeerOM, self).receive(timeout)
        return decoder.decode_bytes(msg)
        
    def send(self, om):
        return super(SCSCPPeerOM, self).send(encoder.encode_bytes(om))

    
class SCSCPClientBase(SCSCPPeer):
    """
    A simple SCSCP synchronous client, with no understanding of OpenMath.
    """
    
    def __init__(self, socket, timeout=30, logger=None):
        super(SCSCPClientBase, self).__init__(socket, timeout, logger, me="Client", you="Server")

    @_assert_status(INITIALIZED, "Session already opened.")
    def connect(self, timeout=None):
        """ SCSCP handshake """
        
        pi = self._get_next_PI([''], timeout=timeout)
        if ('scscp_versions' not in pi.attrs
                or b'1.3' not in pi.attrs['scscp_versions'].split()):
            self.quit()
            raise SCSCPConnectionError("Unsupported SCSCP versions %s." % pi.attrs.get('scscp_versions'), pi)
        
        self.service_info = pi.attrs

        self._send_PI(version=b'1.3')

        pi = self._get_next_PI([''], timeout=timeout)
        if pi.attrs.get('version') != b'1.3':
            self.quit()
            raise SCSCPConnectionError("Server sent unexpected response.", pi)

        self.status = CONNECTED

    @_assert_connected
    def terminate(self, id):
        """ Send SCSCP terminate message """
        self._send_PI('terminate', call_id=id)


class SCSCPClient(SCSCPClientBase, SCSCPPeerOM):
    """
    A simple SCSCP synchronous client.
    """
    def wait(self, timeout=-1):
        return SCSCPProcedureMessage.from_om(self.receive(timeout))

    def call(self, data, cookie=False, **opts):
        if cookie:
            opts['return_cookie'] = True
        elif cookie is None:
            opts['return_nothing'] = True
        else:
            opts['return_object'] = True
        call = SCSCPProcedureMessage.call(data, id=None, **opts)
        self.send(call.om())
        return call
