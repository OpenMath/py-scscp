import socket
from six.moves import socketserver
import logging

from openmath.convert_pickle import PickleConverter as MitMConverter

from scscp.client import TimeoutError, CONNECTED
from scscp.server import SCSCPServer
from scscp.scscp import SCSCPQuit, SCSCPProtocolError
from scscp import scscp

MitMBase = "http://opendreamkit.org/MitM"
MitMCD = "computation"
MitMEval = "sage_eval"

class MitMRequestHandler(socketserver.BaseRequestHandler):
    def __init__(self,converter, *kargs, **kwargs):
        self.converter = converter
        super(socketserver.BaseRequestHandler, self).__init__(*kargs, **kwargs)
    
    def setup(self):
        self.server.log.info("New connection from %s:%d" % self.client_address)
        self.log = self.server.log.getChild(self.client_address[0])
        self.scscp = SCSCPServer(self.request, self.server.name,
                                     self.server.version, logger=self.log)
        
    # TODO: should be inherited from a to-be-written SCSCPRequestHandler class        
    def handle(self):
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
            self.handle_call(call)

    # TODO: most of this should be inherited as well
    def handle_call(self, call):
        if (call.type != 'procedure_call'):
            raise SCSCPProtocolError('Bad message from client: %s.' % call.type, om=call.om())
        try:
            head = call.data.elem.name
            self.log.debug('Requested head: %s...' % head)
            
            if call.data.elem.cd == 'scscp2' and head in CD_SCSCP2:
                res = getattr(self, head)(call.data)
            elif self.data.elem.base == MitMBase and self.data.elem.cd == MitMCD and self.data.elem.name == MitMEval:
                # we take the one argument of MitMEval, import it (which triggers computation), and export it (i.e., the result of the computation)
                obj = call.data.arguments[0]
                objPy = self.converter.to_python(obj)
                res = self.converter.to_openmath(objPy)
            else:
                self.log.debug('...head unknown.')
                return self.scscp.terminated(call.id, om.OMError(
                    om.OMSymbol('unhandled_symbol', cd='error'), [call.data.elem]))

            strlog = str(res)
            self.log.debug('...sending result: %s' % (strlog[:20] + ('...' if len(strlog) > 20 else '')))
            return self.scscp.completed(call.id, res)
        except (AttributeError, IndexError, TypeError):
            self.log.debug('...client protocol error.')
            return self.scscp.terminated(call.id, om.OMError(
                om.OMSymbol('unexpected_symbol', cd='error'), [call.data]))
        except Exception as e:
            self.log.exception('Unhandled exception:')
            return self.scscp.terminated(call.id, 'system_specific',
                                             'Unhandled exception %s.' % str(e))

    def get_allowed_heads(self, data):
        return scscp.symbol_set([om.OMSymbol(base = MitMEval, cd = MitMCD, name = MitMEval)], cdnames=[MitMCD, 'scscp1'])
    
    def is_allowed_head(self, data):
        head = data.arguments[0]
        return conv.to_openmath((head.cdbase == MitMBase and head.cd == MitMCD and head.name == MitMEval)
                              or head.cd == 'scscp1')

    def get_service_description(self, data):
        return scscp.service_description(self.server.name.decode(),
                                             self.server.version.decode(),
                                             self.server.description)

class MitMSCSCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer, object):
    allow_reuse_address = True
    
    def __init__(self, openmath_converter, host='localhost', port=26133,
                     logger=None, name=b'MitM Server', version=b'none',
                     description='MitM SCSCP server'):
        # ThreadingMixIn expects a class as constructor argument, so we have to build one that knows about the converter
        class ReqHandler(MitMRequestHandler):
            def __init__(self, *args, **kwargs):
                super(MitMRequestHandler,self).__init__(openmath_converter, *args, **kwargs)
        super(MitMSCSCPServer, self).__init__((host, port), ReqHandler)
        self.log = logger or logging.getLogger(__name__)
        self.name = name
        self.version = version
        self.description = description
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('demo_server')
    conv = MitMConverter()
    srv = MitMSCSCPServer(conv, logger=logger)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
        srv.server_close()

