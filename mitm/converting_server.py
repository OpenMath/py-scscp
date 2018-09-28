import socket
from six.moves import socketserver
import logging

from openmath.convert_pickle import PickleConverter as MitMConverter

from scscp.client import TimeoutError, CONNECTED
from scscp.server import SCSCPServer
from scscp.scscp import SCSCPQuit, SCSCPProtocolError
from scscp import scscp

from scscp.socketserver import SCSCPServerRequestHandler, SCSCPSocketServer

MitMBase = "http://opendreamkit.org/MitM"
MitMCD = "computation"
MitMEval = "sage_eval"

class MitMRequestHandler(SCSCPServerRequestHandler):
    def __init__(self, converter, *args, **kwargs):
        super(MitMRequestHandler, self).__init__(*args, **kwargs)
        self.converter = converter
    
    def handle_call(self, call, head):
        if self.data.elem.base == MitMBase and self.data.elem.cd == MitMCD and self.data.elem.name == MitMEval:
                # we take the one argument of MitMEval, import it (which triggers computation), and export it (i.e., the result of the computation)
                obj = call.data.arguments[0]
                objPy = self.converter.to_python(obj)
                return self.converter.to_openmath(objPy)
        
        return super(MitMRequestHandler, self).handle_call(call, head)

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

class MitMSCSCPServer(SCSCPSocketServer):
    def __init__(self, openmath_converter, host='localhost', port=26133,
                     logger=None, name=b'MitM Server', version=b'none',
                     description='MitM SCSCP server'):
        
        # build a converter class
        class ReqHandler(MitMRequestHandler):
            def __init__(self, *args, **kwargs):
                super(MitMRequestHandler,self).__init__(openmath_converter, *args, **kwargs)
        
        super(MitMSCSCPServer, self).__init__(host=host, port=port, 
            logger=logger or logging.getLogger(__name__), name=name, version=version, 
            description=description, RequestHandlerClass=ReqHandler)
        
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

