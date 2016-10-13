import logging
import io
from pexpect import fdpexpect, TIMEOUT, EOF
from openmath import encoder, decoder
from . import scscp
from .scscp import SCSCPConnectionError, SCSCPCancel, SCSCPProcedureMessage
from .processing_instruction import ProcessingInstruction as PI

class SCSCPPeer():
    """
    Base class for SCSCP client and server
    """
    
    INITIALIZED=0
    CONNECTED=1
    CLOSED=2
    
    def __init__(self, socket, timeout=30, logger=None, me='Client', you='Server'):
        self.socket = socket
        self.stream = fdpexpect.fdspawn(socket.makefile(), timeout=timeout)
        self.status = self.INITIALIZED
        self.log = logger or logging.getLogger(__name__)
        self.me, self.you = me, you

    def _assert_status(status, msg=None):
        def wrap(fun):
            def wrapper(self, *args, **kwds):
                if self.status != status:
                    raise RuntimeError(msg or "Bad status %d." % self.status)
                return fun(self, *args, **kwds)
            return wrapper
        return wrap
    _assert_connected = _assert_status(CONNECTED, "Client not connected.")

    def _get_next_PI(self, expect=None, timeout=-1):
        while True:
            try:
                self.stream.expect(PI.PI_regex, timeout=timeout)
            except TIMEOUT:
                self.quit()
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
                    raise SCSCPConnectionError("%s closed session (reason: %s)." % (self.you, pi.attrs.get('reason')), pi)
                if pi.key == 'info':
                    self.log.info("SCSCP info: %s " % pi.attrs.get('info'))
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
            pi = self._get_next_PI(['end', 'cancel', 'info'], timeout=timeout)
            if pi.key == 'cancel':
                raise SCSCPCancel('%s canceled transmission' % self.you)
            
            msg += self.stream.before
            if pi.key == 'info':
                continue
            else:
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
            self.status = self.CLOSED

    @_assert_connected
    def info(self, info):
        """ Send SCSCP info message """
        self._send_PI(info=info)


class SCSCPClientBase(SCSCPPeer):
    """
    A simple SCSCP synchronous client, with no understanding of OpenMath.
    """
    
    def __init__(self, socket, timeout=30, logger=None):
        super(SCSCPClientBase, self).__init__(socket, timeout, logger, me="Client", you="Server")

    @SCSCPPeer._assert_status(SCSCPPeer.INITIALIZED, "Session already opened.")
    def connect(self):
        """ SCSCP handshake """
        
        pi = self._get_next_PI([''])
        if ('scscp_versions' not in pi.attrs
                or b'1.3' not in pi.attrs['scscp_versions'].split()):
            self.quit()
            raise SCSCPConnectionError("Unsupported SCSCP versions %s." % pi.attrs.get('scscp_versions'), pi)
        
        self.service_info = pi.attrs

        self._send_PI(version=b'1.3')

        pi = self._get_next_PI([''])
        if pi.attrs.get('version') != b'1.3':
            self.quit()
            raise SCSCPConnectionError("Server sent unexpected response.", pi)

        self.status = self.CONNECTED

    @SCSCPPeer._assert_connected
    def terminate(self, id):
        """ Send SCSCP terminate message """
        self._send_PI('terminate', call_id=id)


class SCSCPClient(SCSCPClientBase):
    """
    A simple SCSCP synchronous client.
    """
    def receive(self, timeout=-1):
        msg = super(SCSCPClient, self).receive(timeout)
        return decoder.decode_stream(io.BytesIO(msg))
        
    def send(self, om):
        return super(SCSCPClient, self).send(encoder.encode_stream(om))

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
