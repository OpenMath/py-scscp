import unittest
import socket, time
from threading import Thread

from scscpy.client import SCSCPClient

class TestConnInit(unittest.TestCase):
    def test_successful(self):
        """ Test a successful connection initiation """
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("localhost", 26133))
        server.listen(1)
        
        def run(server):
            cs, _ = server.accept()
            cs.send(b'<?scscp scscp_versions="1.3"?>')
            cs.recv(100)
            cs.send(b'<?scscp version="1.3"?>')
            cs.recv(100)
        Thread(target=run, args=(server,)).start()

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("localhost", 26133))
        scscp = SCSCPClient(client)

        scscp.connect()
        self.assertEqual(scscp.status, SCSCPClient.CONNECTED, "Connected")
        self.assertEqual(scscp.service_info, {'scscp_versions': b'1.3'}, "Connected")
        
        scscp.quit()
        self.assertEqual(scscp.status, SCSCPClient.CLOSED, "Quitted")
