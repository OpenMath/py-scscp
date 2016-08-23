import re

PI_regex = re.compile(b"<\?scscp\s+(.{0,4084}?)\?>", re.S)
PI_regex_full = re.compile(b'^<\?scscp(?:\s+(?P<key>\w+))?(?P<attrs>(?:\s+\w+=".*?")*)\s*\?>$')
PI_regex_attr = re.compile(b'(\w+)="(.*?)"')

class SCSCPError(RuntimeError):
    pass
class SCSCPCancel(SCSCPError):
    def __init__(self):
        super(SCSCPCancel, self).__init__('Server canceled transmission')

class ProcessingInstruction():
    @classmethod
    def parse(cls, bytes):
        match = PI_regex_full.match(bytes)
        if match:
            key = (match.group('key') or b'').decode('ascii')
            attrs = { k.decode('ascii'): v
                          for k, v in PI_regex_attr.findall(match.group('attrs')) }
            return cls(key, **attrs)
        else:
            raise SCSCPError("Bad SCSCP processing instruction %s." % bytes)

    def __init__(self, key='', **attrs):
        self.key = key
        self.attrs = attrs

    def __bytes__(self):
        print(self.key)
        return b'<?scscp %s %s ?>' % (self.key.encode(),
                                         b' '.join(b'%s="%s"' % (k.encode(), v)
                                                      for k,v in self.attrs.items()))

    def __str__(self):
        return bytes(self).decode('ascii')
    
    def __repr__(self):
        return 'ProcessingInstruction: %s' % self
