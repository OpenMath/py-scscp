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
    if errors['error_' + error] and msg is None:
        raise RuntimeError('Must give an error message')
    else:
        data = om.OMError(om.OMSymbol('error_' + error, cd='scscp1'), om.OMString(msg))
        return  _procedure_end('procedure_terminated', id, data, **info)
