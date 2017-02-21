import unittest
import socket
from threading import Thread
from collections import OrderedDict

from scscp import client
from scscp.client import SCSCPClientBase
from scscp.server import SCSCPServerBase

class TestConnInit(unittest.TestCase):
    def setUp(self):
        server, client = socket.socketpair()
        self.client = SCSCPClientBase(client)
        self.server = SCSCPServerBase(server, name=b'Test', version=b'none', id=b'test-id')

    def test_successful(self):
        """ Test a successful connection initiation """
        t = Thread(target=self.server.accept)
        t.start()
        self.client.connect()
        t.join()

        self.assertEqual(self.client.status, client.CONNECTED, "Connected")
        self.assertEqual(OrderedDict(self.client.service_info.items()),
                             OrderedDict([
                                 ('service_name', b'Test'),
                                 ('service_version', b'none'),
                                 ('service_id', b'test-id'),
                                 ('scscp_versions', b'1.3')
                                 ]), "Connected")
        
        self.client.quit()
        self.assertEqual(self.client.status, client.CLOSED, "Quitted")

    def test_msg(self):
        """ Test a message exchange """
        t = Thread(target=self.server.accept)
        t.start()
        self.client.connect()
        t.join()
        
        self.client.send(b"Hello world!")

        msg = self.server.receive()
        self.assertEqual(msg, b"\nHello world!\n")
        
        self.server.send(msg)
        msg = self.client.receive()
        self.assertEqual(msg, b"\n\nHello world!\n\n")

        self.server.quit()
        self.assertEqual(self.server.status, client.CLOSED, "Quitted")
