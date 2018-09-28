import os
import logging

from six.moves import socketserver

from .server import SCSCPServer
from .scscp import SCSCPQuit, SCSCPProtocolError, SCSCPUnknownHead, SCSCPProcedureMessage

from openmath import openmath as om

# built-in messages
CD_SCSCP2 = ['get_service_description', 'get_allowed_heads', 'is_allowed_head']


class SCSCPServerRequestHandler(socketserver.BaseRequestHandler):
    """ A request handler for an SCSCP Server """

    def setup(self):
        """ Setups of this request handler """
        self.server.log.info("New connection from %s:%d" % self.client_address)
        self.log = self.server.log.getChild(self.client_address[0])
        self.scscp = SCSCPServer(self.request, self.server.name,
                                 self.server.version, logger=self.log)

    def handle(self):
        """ Handles a single new connection """
        self.scscp.accept()
        while True:
            try:
                call = self.scscp.wait()
            except TimeoutError:
                continue
            except SCSCPQuit as e:
                self.log.info(e)
                break
            except ConnectionResetError:
                self.log.info('Client closed unexpectedly.')
                break
            except SCSCPProtocolError as e:
                self.log.info('SCSCP protocol error: %s.' % str(e))
                self.log.info('Closing connection.')
                self.scscp.quit()
                break
            self.__handle_call(call)

    def __handle_call(self, call):
        """ Safely handles a call """

        if (call.type != 'procedure_call'):
            raise SCSCPProtocolError(
                'Bad message from client: %s.' % call.type, om=call.om())

        try:
            head = call.data.elem.name
            self.log.debug('Requested head: %s...' % head)

            # for the methods in scscp2, use the class methods
            if call.data.elem.cd == 'scscp2':
                if not head in CD_SCSCP2:
                    raise SCSCPUnknownHead
                res = getattr(self, head)(call.data)

            # else, handle the call internally
            else:
                res = self.handle_call(call, head)

            strlog = str(res)
            self.log.debug('...sending result: %s' %
                           (strlog[:20] + ('...' if len(strlog) > 20 else '')))

            # if we already constructed a procedure message
            # else just return it as is
            if isinstance(res, SCSCPProcedureMessage):
                return res
            # else,
            else:
                return self.scscp.completed(call.id, res)

        # User-thrown execption: I don't know this head
        except SCSCPUnknownHead:
            self.log.debug('...head unknown.')
            return self.scscp.terminated(call.id, om.OMError(
                om.OMSymbol('unhandled_symbol', cd='error'), [call.data.elem]))

        # we tried to look up something, but it wasn't given by the client
        except (AttributeError, IndexError, TypeError):
            self.log.debug('...client protocol error.')
            return self.scscp.terminated(call.id, om.OMError(
                om.OMSymbol('unexpected_symbol', cd='error'), [call.data]))

        # anything else
        except Exception as e:
            self.log.exception('Unhandled exception:')
            return self.scscp.terminated(call.id, 'system_specific',
                                         'Unhandled exception %s.' % str(e))

    def handle_call(self, call, head):
        """ Handles a call and may throw exceptions """

        raise SCSCPUnknownHead

    def get_allowed_heads(self, data):
        raise NotImplementedError

    def is_allowed_head(self, data):
        raise NotImplementedError

    def get_service_description(self, data):
        raise NotImplementedError


class SCSCPSocketServer(socketserver.ThreadingMixIn, socketserver.TCPServer, object):
    allow_reuse_address = True

    def __init__(self, host=None, port=None,
                 logger=None, name=b'SCSCPSocketServer', version=b'none',
                 description='SCSCP socket server', RequestHandlerClass=SCSCPServerRequestHandler):

        # if host is not given, try the HOST environment variable
        if host is None:
            host = os.getenv('HOST', 'localhost')

        # if port is not given, try the PORT environment variable
        if port is None:
            port = os.getenv('PORT', '26133')
        port = int(port)

        # super call
        super(SCSCPSocketServer, self).__init__(
            (host, port), RequestHandlerClass)
        self.log = logger or logging.getLogger(__name__)
        self.name = name
        self.version = version
        self.description = description
