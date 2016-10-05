import unittest
import socket
from threading import Thread

from scscp.client import SCSCPClient

class TestConnInit(unittest.TestCase):
    def setUp(self):
        self.server, client = socket.socketpair()
        self.client = SCSCPClient(client)

    def test_successful(self):
        """ Test a successful connection initiation """
        self.server.send(b'<?scscp scscp_versions="1.3"?><?scscp version="1.3"?>')
        self.client.connect()

        self.assertEqual(self.client.status, SCSCPClient.CONNECTED, "Connected")
        self.assertEqual(self.client.service_info, {'scscp_versions': b'1.3'}, "Connected")
        
        self.client.quit()
        self.assertEqual(self.client.status, SCSCPClient.CLOSED, "Quitted")

    def test_msg(self):
        """ Test a message exchange """
        self.server.send(b'<?scscp scscp_versions="1.3"?><?scscp version="1.3"?>')
        self.client.connect()
        self.server.recv(100)
        
        self.client.send("Hello world!")

        msg = self.server.recv(100)
        self.assertEqual(msg, b"<?scscp start  ?>Hello world!<?scscp end  ?>")
        
        self.server.send(msg)
        msg = self.client.receive()
        self.assertEqual(msg, b"Hello world!")
