from demo_server import Server
from scscp import SCSCPCLI
from openmath import convert, openmath as om
from sage.rings.integer_ring import Integer

def ZZ_to_OM(integer):
    return om.OMInteger(int(integer))
def OM_TO_ZZ(integer):
    return Integer(integer.integer)
convert.register(Interger, ZZ_to_OM, om.OMInteger, OM_TO_ZZ)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('demo_server_sage')
    srv = Server(logger=logger)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
        srv.server_close()
