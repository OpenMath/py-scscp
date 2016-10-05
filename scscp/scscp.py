class SCSCPError(RuntimeError):
    pass
class SCSCPConnectionError(SCSCPError):
    def __init__(self, msg, pi=None):
        super(SCSCPConnectionError, self).__init__(msg)
        self.pi = pi
class SCSCPCancel(SCSCPError):
    pass
