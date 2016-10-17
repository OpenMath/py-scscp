import socket
from openmath import convert, openmath as om
from .client import SCSCPClient
from . import scscp

def _conv_if_py(obj):
    if isinstance(obj, om.OMAny):
        return obj
    else:
        return convert.to_openmath(obj)

class SCSCPCLI(SCSCPClient):
    """ A synchronous CLI client for SCSCP """

    class Head(object):
        """ A callable remote procedure """
        def __init__(self, name, cd, cli):
            self._name = name
            self.cd = cd
            self._cli = cli
            self._om = om.OMSymbol(name, cd=cd)
        def __call__(self, data, cookie=False, **opts):
            res = self._cli._call_wait(om.OMApplication(self._om, map(_conv_if_py, data)),
                                           cookie, **opts)
            if res.type == 'procedure_completed':
                try:
                    return convert.to_python(res.data)
                except ValueError:
                    return res.data
            elif res.type == 'procedure_terminated':
                raise scscp.SCSCPProtocolError('Server returned error: %s.' % res.data.name.name,
                                                   res.data)
            else:
                raise scscp.SCSCPProtocolError('Unexpected response.', resp.om())
    
    class CD(object):
        """ A content dictionary, implemented as a namespace """
        def __init__(self, name, cli):
            self._name = name
            self._cli = cli
        def __getattr__(self, attr):
            return SCSCPCLI.Head(attr, self._name, self._cli)
        def _get_head(self, name):
            head = self.__dict__.get(name)
            if head is None:
                head = self.__dict__[name] = getattr(self, name)
            return head
        def __repr__(self):
            return repr([ k for k in self.__dict__ if k[0] != '_' ])
        def __contains__(self, head):
            return head in self.__dict__
    
    class Heads(object):
        """ A list of remote procedures """
        def __init__(self, cli):
            self._cli = cli
        def __getattr__(self, attr):
            return SCSCPCLI.CD(attr, self._cli)
        def _get_cd(self, name):
            cd = self.__dict__.get(name)
            if cd is None:
                cd = self.__dict__[name] = getattr(self, name)
            return cd
        def __repr__(self):
            return repr({ k:v for k,v in self.__dict__.items() if k[0] != '_' })
        def __contains__(self, cd):
            return cd in self.__dict__
            
    
    def __init__(self, host, port=26133, populate=True):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        super(SCSCPCLI, self).__init__(s)
        self.heads = self.Heads(self)
        self.connect()
        if populate:
            self.populate_heads()

    def _call_wait(self, data, cookie=False, **opts):
        call = self.call(data, cookie, **opts)
        resp = self.wait()
        
        if resp.id != call.id:
            raise scscp.SCSCPProtocolError("Wrong call id (expected %s, got %s)."
                                               % (call.id, resp.id), resp.om())

        return resp

    def populate_heads(self):
        heads = self._call_wait(scscp.get_allowed_heads())
        if heads.type == 'procedure_terminated':
            raise scscp.SCSCPProtocolError("Failed to get heads (%s)." % heads.data.name.name,
                                               heads.data)
        elif heads.type != 'procedure_completed':
            raise scscp.SCSCPProtocolError("Server gave unexpected response.", heads.om())
    
        try:
            for symbol in heads.data.arguments:
                if isinstance(symbol, om.OMSymbol):
                    self.heads._get_cd(symbol.cd)._get_head(symbol.name)
                elif symbol.elem.name == 'CDName':
                    self.heads._get_cd(symbol.arguments[0].string)
                else:
                    continue
        except (AttributeError, IndexError):
            raise scscp.SCSCPProtocolError("Server gave unexpected response.", heads.data)

    def is_allowed_head(self, name, cd):
        return self.heads.scscp2.is_allowed_head([om.OMSymbol(name, cd)])
    
    def get_description(self):
        return '\n'.join(a.string for a in self.heads.scscp2.get_service_description([]).arguments)
