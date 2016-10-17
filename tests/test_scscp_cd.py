import unittest
from scscp import scscp
from openmath.openmath import *

class TestSCSCPCD(unittest.TestCase):
    def test_service_description(self):
        self.assertEqual(scscp.get_service_description(),
                             OMApplication(
                                 OMSymbol('get_service_description', 'scscp2', id=None, cdbase=None),
                                 [], id=None, cdbase=None))

        self.assertEqual(scscp.service_description('Hello', 'world'),
                             OMApplication(
                                 OMSymbol('service_description', 'scscp2', id=None, cdbase=None),
                                 [OMString('Hello', id=None), OMString('world', id=None)],
                                 id=None, cdbase=None))

    def test_procedure(self):
        self.assertEqual(scscp.SCSCPProcedureMessage.call(scscp.get_service_description(), id='myid').om(),
                             OMObject( OMAttribution( OMAttributionPairs(
                                 [(OMSymbol('call_id', 'scscp1',), OMString('myid'))]),
                                 OMApplication(
                                     OMSymbol('procedure_call', 'scscp1'),
                                     [OMApplication(
                                         OMSymbol('get_service_description', 'scscp2'), [])]))))
