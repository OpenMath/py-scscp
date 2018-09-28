import logging

from six.moves import socketserver

from openmath import openmath as om, convert as conv

from scscp import scscp
from scscp.socketserver import SCSCPServerRequestHandler, SCSCPSocketServer, CD_SCSCP2

# Supported functions
CD_ARITH1 = {
    'abs'         : abs,
    'unary_minus' : lambda x  : -x,
    'minus'       : lambda x,y: x-y,
    'plus'        : lambda x,y: x+y,
    'divide'      : lambda x,y: x/y,
    'times'       : lambda x,y: x*y,
    'power'       : lambda x,y: x**y,
}

class DemoServerRequestHandler(SCSCPServerRequestHandler):
    def handle_call(self, call, head):
        if call.data.elem.cd == 'arith1' and head in CD_ARITH1:
            args = [conv.to_python(a) for a in call.data.arguments]
            return conv.to_openmath(CD_ARITH1[head](*args))
        
        return super(SCSCPRequestHandler, self).handle_call(call, head)

    def get_allowed_heads(self, data):
        return scscp.symbol_set([om.OMSymbol(head, cd='scscp2') for head in CD_SCSCP2]
                                    + [om.OMSymbol(head, cd='arith1') for head in CD_ARITH1],
                                    cdnames=['scscp1'])
    
    def is_allowed_head(self, data):
        head = data.arguments[0]
        return conv.to_openmath((head.cd == 'arith1' and head.name in CD_ARITH1)
                                    or (head.cd == 'scscp2' and head.name in CD_SCSCP2)
                                    or head.cd == 'scscp1')

    def get_service_description(self, data):
        return scscp.service_description(self.server.name.decode(),
                                             self.server.version.decode(),
                                             self.server.description)

class Server(SCSCPSocketServer):
    def __init__(self, host='localhost', port=26133,
                     logger=None, name=b'DemoServer', version=b'none',
                     description='Demo SCSCP server'):

        super(Server, self).__init__(host=host, port=port, logger=logger or logging.getLogger(__name__), 
            name=name, version=version, description=description, 
            RequestHandlerClass=DemoServerRequestHandler)
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('demo_server')
    srv = Server(logger=logger)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
        srv.server_close()

