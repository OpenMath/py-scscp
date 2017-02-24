import unittest
import time, sys
from threading import Thread

from scscp.cli import SCSCPCLI
from demo_server import Server

class TestCli(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.server_t = Thread(target=self.server.serve_forever)
        self.server_t.daemon = True
        self.server_t.start()
        self.client = SCSCPCLI('localhost', populate=False)

    def tearDown(self):
        self.client.quit()
        self.server.shutdown()
        self.server.server_close()
        self.server_t.join()
        
    @unittest.skipIf((sys.version_info.major, sys.version_info.minor) < (3,4),
                     "assertLogs not supported in Python < 3.4")
    def test_info(self):
        with self.assertLogs('demo_server', 'INFO') as log:
            self.client.info(b'Hello world')
            time.sleep(0.1)
        self.assertEqual(log.output, ['INFO:demo_server.127.0.0.1:SCSCP info: Hello world'])

    def test_populate(self):
        self.client.populate_heads()
        self.assertTrue('scscp1' in self.client.heads)
        self.assertTrue('scscp2' in self.client.heads)
        self.assertTrue('arith1' in self.client.heads)
        self.assertTrue('plus' in self.client.heads.arith1)
        self.assertTrue('minus' in self.client.heads.arith1)
        
        self.assertFalse('not_a_cd' in self.client.heads)
        self.assertFalse('not_a_head' in self.client.heads.scscp1)
        self.assertFalse('not_a_head' in self.client.heads.not_a_cd)

    def test_two_clients(self):
        client = SCSCPCLI('localhost')
        client.quit()
        self.assertEqual(client.status, 2)

    def test_description(self):
        self.assertEqual(self.client.get_description(), ["DemoServer", "none", "Demo SCSCP server"])

    def test_arith(self):
        cases = [
            ('plus', (1, 2), 3),
            ('minus', (1, 2), -1),
            ('times', (1, 2), 2),
            ('divide', (3, 2), 3/2),
            ('unary_minus', (-1,), 1),
            ('abs', (-1,), 1),
            ('power', (2, 2), 4),
            ('power', (2, 100), 2**100),            
            ('plus', (1.0, 2.0), 3.0),
            #('power', (2, 3.1), 2**3.1), fails in Python 2
            ('plus', ('a', 'b'), 'ab'),
        ]
        for head, ins, out in cases:
            self.assertEqual(out, getattr(self.client.heads.arith1, head)(ins),
                                 "Testing arith1.%s" % head)
