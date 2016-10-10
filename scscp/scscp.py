import uuid
import openmath.openmath as om
import itertools

class SCSCPError(RuntimeError):
    pass
class SCSCPConnectionError(SCSCPError):
    def __init__(self, msg, pi=None):
        super(SCSCPConnectionError, self).__init__(msg)
        self.pi = pi
class SCSCPCancel(SCSCPError):
    pass

### SCSCP1 content dictionary

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

def call_id(id=None):
    return (om.OMSymbol('call_id', cd='scscp1'), om.OMString(str(id or uuid.uuid1())))
            
def _procedure(type, data, id=None, params=None):
    return om.OMObject(
        om.OMAttribution(
            om.OMAttributionPairs([call_id(id)] + (params or [])),
            om.OMApplication(
                om.OMSymbol(type, cd='scscp1'),
                [data]
            )
        )
    )

def procedure_call(data, id=None, **opts):
    opts = [(om.OMSymbol('option_' + k, cd='scscp1'),
                 options['option_' + k](v))
                for k, v in opts.items()]
    return _procedure('procedure_call', data, id, opts)

def _procedure_end(type, id, data, **info):
    info = [(om.OMSymbol('info_' + k, cd='scscp1'),
                 infos['info_' + k](v))
                for k, v in info.items()]
    return _procedure(type, data, id, info)

def procedure_completed(id, data, **info):
    return _procedure_end('procedure_completed', id, data, **info)

def procedure_terminated(id, error, msg=None, **info):
    if not isinstance(error, om.OMError):
        if errors['error_' + error] and msg is None:
            raise RuntimeError('Must give an error message')
        error = om.OMError(om.OMSymbol('error_' + error, cd='scscp1'), om.OMString(msg))
    return  _procedure_end('procedure_terminated', id, error, **info)


### SCSCP2 content dictionary

def _apply(cmd, data):
    return om.OMApplication(om.OMSymbol(cmd, cd='scscp2'), data)

def symbol_set(symbols, cdnames=['scscp1', 'scscp2'], cdurls=[], groupnames=[], groupurls=[]):
    aggregations = (
        (cdnames, om.OMSymbol('CDName', cd='meta')),
        (cdurls, om.OMSymbol('CDURL', cd='meta')),
        (groupnames, om.OMSymbol('CDGroupName', cd='metagrp')),
        (groupurls, om.OMSymbol('CDGroupURL', cd='metagrp')),
    )
    
    return _apply('symbol_set', symbols
                      + sum([[om.OMApplication(symbol, om.OMString(x)) for x in list]
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
    return om.OMError(om.OMSymbol('no_such_transient_cd', cd='scscp2'), om.OMString(cd))
