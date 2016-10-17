import re
from .scscp import SCSCPConnectionError

class ProcessingInstruction():
    PI_regex = re.compile(b"<\?scscp\s+(.{0,4084}?)\?>", re.S)
    PI_regex_full = re.compile(b'^<\?scscp(?:\s+(?P<key>\w+))?(?P<attrs>(?:\s+\w+=".*?")*)\s*\?>$')
    PI_regex_attr = re.compile(b'(\w+)="(.*?)"')

    @classmethod
    def parse(cls, bytes):
        match = cls.PI_regex_full.match(bytes)
        if match:
            key = (match.group('key') or b'').decode('ascii')
            attrs = { k.decode('ascii'): v
                          for k, v in cls.PI_regex_attr.findall(match.group('attrs')) }
            return cls(key, **attrs)
        else:
            raise SCSCPConnectionError("Bad SCSCP processing instruction %s." % bytes)

    def __init__(self, key='', **attrs):
        self.key = key
        self.attrs = attrs

    def __bytes__(self):
        return b'<?scscp %s %s ?>' % (self.key.encode(),
                                         b' '.join(b'%s="%s"' % (k.encode(), v)
                                                      for k,v in self.attrs.items()))

    def __str__(self):
        return '<?scscp %s %s ?>' % (self.key,
                                         ' '.join('%s="%s"' % (k, v.decode())
                                                      for k,v in self.attrs.items()))
    
    def __repr__(self):
        return 'ProcessingInstruction: %s' % self
