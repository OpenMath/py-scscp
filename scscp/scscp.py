import uuid
import openmath.openmath as om

class SCSCPError(RuntimeError):
    pass
class SCSCPConnectionError(SCSCPError):
    def __init__(self, msg, pi=None):
        super(SCSCPConnectionError, self).__init__(msg)
        self.pi = pi
class SCSCPCancel(SCSCPError):
    pass
class SCSCPQuit(SCSCPError):
    def __init__(self, msg, reason=''):
        super(SCSCPQuit, self).__init__(msg)
        self.reason = reason
class SCSCPProtocolError(SCSCPError):
    def __init__(self, msg, om=None):
        super(SCSCPProtocolError, self).__init__(msg)
        self.om = om

### SCSCP1 content dictionary

class SCSCPProcedureMessage(object):
    options = {
        'debuglevel'     : om.OMInteger,
        'max_memory'     : om.OMInteger,
        'min_memory'     : om.OMInteger,
        'return_cookie'  : om.OMString,
        'return_object'  : om.OMString,
        'return_nothing' : om.OMString,
        'runtime'        : om.OMInteger,
    }

    infos = {
        'memory'  : om.OMInteger,
        'runtime' : om.OMInteger,
        'message' : om.OMString,
    }

    # Whether error message is mandatory
    errors = {
        'memory'          : False,
        'runtime'         : False,
        'system_specific' : True,
    }

    def __init__(self, type, data, id=None, params=None):
        self.type = type
        self.id = str(id or uuid.uuid1())
        self.params = params or []
        self.data = data

    @classmethod
    def call(cls, data, id=None, **opts):
        opts = [(om.OMSymbol('option_' + k, cd='scscp1'),
                    cls.options[k](v))
                    for k, v in opts.items() if v is not None and v is not False]
        return cls('procedure_call', data, id, opts)

    @classmethod
    def _w_info(cls, type, id, data, **info):
        info = [(om.OMSymbol('info_' + k, cd='scscp1'),
                    cls.infos[k](v))
                    for k, v in info.items() if v is not None]
        return cls(type, data, id, info)

    @classmethod
    def completed(cls, id, data, **info):
        return cls._w_info('procedure_completed', id, data, **info)

    @classmethod
    def terminated(cls, id, error, msg=None, **info):
        if not isinstance(error, om.OMError):
            if cls.errors[error] and msg is None:
                raise RuntimeError('Must give an error message')
            error = om.OMError(om.OMSymbol('error_' + error, cd='scscp1'), [om.OMString(msg)])
        return cls._w_info('procedure_terminated', id, error, **info)

    def __repr__(self):
        return "SCSCPProcedureMessage %s#%s" % (self.type, self.id)

    def __eq__(self, other):
        return (isinstance(other, SCSCPProcedureMessage)
                    and self.type == other.type and self.id == other.id
                    and self.params == other.params and self.data == other.data)
    
    def om(self):
        return om.OMObject(
            om.OMAttribution(
                om.OMAttributionPairs([(om.OMSymbol('call_id', cd='scscp1'), om.OMString(self.id))] + self.params),
                om.OMApplication(
                    om.OMSymbol(self.type, cd='scscp1'),
                    [self.data]
                )
            )
        )
        
    @classmethod
    def from_om(cls, obj):
        if not (isinstance(obj, om.OMObject)
                and isinstance(obj.omel, om.OMAttribution)):
            raise SCSCPProtocolError('Bad SCSCP procedure message.', obj)
        params = obj.omel.pairs.pairs

        try:
            index, id = next((i,p) for i,p in enumerate(params)
                                 if p[0].name == 'call_id' and p[0].cd == 'scscp1')
        except StopIteration:
            raise SCSCPProtocolError('SCSCP procedure message does not contain id.', obj)
        if not isinstance(id[1], om.OMString):
            raise SCSCPProtocolError('Bad SCSCP procedure message.', obj)
        params.pop(index)
        id = id[1].string

        if not (isinstance(obj.omel.obj, om.OMApplication)
                    and obj.omel.obj.elem.cd == 'scscp1'
                    and len(obj.omel.obj.arguments) == 1):
            raise SCSCPProtocolError('Bad SCSCP procedure message.', obj)
        type = obj.omel.obj.elem.name
        data = obj.omel.obj.arguments[0]

        return cls(type, data, id, params)
        

### SCSCP2 content dictionary

def _apply(cmd, data):
    return om.OMApplication(om.OMSymbol(cmd, cd='scscp2'), data)

def symbol_set(symbols=[], cdnames=['scscp1', 'scscp2'], cdurls=[], groupnames=[], groupurls=[]):
    aggregations = (
        (cdnames, om.OMSymbol('CDName', cd='meta')),
        (cdurls, om.OMSymbol('CDURL', cd='meta')),
        (groupnames, om.OMSymbol('CDGroupName', cd='metagrp')),
        (groupurls, om.OMSymbol('CDGroupURL', cd='metagrp')),
    )
    return _apply('symbol_set', symbols
                      + sum([[om.OMApplication(symbol, [om.OMString(x)]) for x in list]
                                 for (list, symbol) in aggregations], []))

def get_allowed_heads():
    return _apply('get_allowed_heads', [])

def is_allowed_head(name, cd):
    return  _apply('is_allowed_head', [om.OMSymbol(name, cd)])

def store(data, peristent=False):
    return _apply('store_' + ('persistent' if persistent else 'session'), [data])

def retrieve(url):
    return _apply('retrieve', [om.OMReference(url)])

def unbind(url):
    return _apply('unbind', [om.OMReference(url)])

def get_transient_cd(name):
    return _apply('get_transient_cd', [om.OMApply(
        om.OMSymbol('CDName', cd='meta'), [om.OMString(name)]
    )])

def get_signature(name, cd):
    return  _apply('get_signature', [om.OMSymbol(name, cd)])

def signature(name, cd, symbol_sets=None, min=None, max=None):
    if isinstance(symbol_sets, list):
        n = len(symbol_sets)
        if min is None:
            min = om.OMInteger(n)
        else:
            assert min <= n, "Too few parameters"
            min = om.OMInteger(min)
        assert max is None or max == n, "Too many parameters"
        max = om.OMInteger(n)
        symbol_sets = om.OMApplication(om.OMSymbol('list', cd='list1'), symbol_sets)
    else:
        min = om.OMInteger(0 if min is None else min)
        max = om.OMSymbol('infinity', cd='nums1') if max is None else om.OMInteger(max)
        if symbol_sets is None:
            symbol_sets = om.OMSymbol('symbol_set_all', cd='scscp2')
    return _apply('signature', [om.OMSymbol(name, cd), min, max, symbol_sets])

def get_service_description():
    return _apply('get_service_description', [])

def service_description(*desc):
    return _apply('service_description', [om.OMString(d) for d in desc])

def no_such_transient_cd(cd):
    return om.OMError(om.OMSymbol('no_such_transient_cd', cd='scscp2'), [om.OMString(cd)])
