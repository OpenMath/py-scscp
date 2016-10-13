import unittest
import socket
from threading import Thread

from scscp.client import SCSCPClientBase
from scscp.server import SCSCPServerBase

class TestConnInit(unittest.TestCase):
    def setUp(self):
        server, client = socket.socketpair()
        self.client = SCSCPClientBase(client)
        self.server = SCSCPServerBase(server)

    def test_successful(self):
        """ Test a successful connection initiation """
        t = Thread(target=self.server.accept)
        t.start()
        self.client.connect()
        t.join()

        self.assertEqual(self.client.status, SCSCPClientBase.CONNECTED, "Connected")
        self.assertEqual(self.client.service_info, {'scscp_versions': b'1.3'}, "Connected")
        
        self.client.quit()
        self.assertEqual(self.client.status, SCSCPClientBase.CLOSED, "Quitted")

    def test_msg(self):
        """ Test a message exchange """
        t = Thread(target=self.server.accept)
        t.start()
        self.client.connect()
        t.join()
        
        self.client.send(b"Hello world!")

        msg = self.server.receive()
        self.assertEqual(msg, b"Hello world!")
        
        self.server.send(msg)
        msg = self.client.receive()
        self.assertEqual(msg, b"Hello world!")

        self.server.quit()
        self.assertEqual(self.server.status, SCSCPClientBase.CLOSED, "Quitted")
