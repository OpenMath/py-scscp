import unittest
import socket
from threading import Thread
import openmath.openmath as om
from openmath.encoder import encode_bytes
from openmath.decoder import decode_bytes

from scscp.client import SCSCPClient
from scscp.server import SCSCPServerBase
from scscp import scscp

class TestClient(unittest.TestCase):
    def setUp(self):
        server, client = socket.socketpair()
        self.client = SCSCPClient(client)
        self.server = SCSCPServerBase(server)
        t = Thread(target=self.server.accept)
        t.start()
        self.client.connect()
        t.join()

    def tearDown(self):
        self.client.quit()
        
    def test_call_wait(self):
        """ Test a procedure call and wait """
        call = self.client.call(scscp.get_allowed_heads())
        self.assertEqual(call.type, "procedure_call")
        self.assertEqual(call.params, [(om.OMSymbol('option_return_object', 'scscp1'), om.OMString(True))])
        self.assertEqual(call.data, om.OMApplication(om.OMSymbol('get_allowed_heads', 'scscp2'), []))

        msg = decode_bytes(self.server.receive())
        self.assertEqual(msg, om.OMObject(om.OMAttribution(
            om.OMAttributionPairs([
                (om.OMSymbol('call_id', 'scscp1'), om.OMString(call.id)),
                (om.OMSymbol('option_return_object', 'scscp1'), om.OMString('True'))
            ]),
            om.OMApplication(om.OMSymbol('procedure_call', 'scscp1'), [
                om.OMApplication(om.OMSymbol('get_allowed_heads', 'scscp2'), [])])
        ), version='2.0'))

        comp = scscp.SCSCPProcedureMessage.completed(call.id, scscp.symbol_set())
        self.server.send(encode_bytes(comp.om()))

        resp = self.client.wait()
        self.assertEqual(resp.type, "procedure_completed")
        self.assertEqual(resp.id, call.id)
        self.assertEqual(resp.params, [])
        self.assertEqual(resp.data, om.OMApplication(
            om.OMSymbol('symbol_set', 'scscp2'),
            [om.OMApplication(om.OMSymbol('CDName', 'meta'), [om.OMString('scscp1')]),
                 om.OMApplication(om.OMSymbol('CDName', 'meta'), [om.OMString('scscp2')])
            ]
        ))
