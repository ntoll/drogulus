# -*- coding: utf-8 -*-
"""
A rather silly test but added all the same for completeness and to check the
initial test suite works as expected.
"""
from drogulus.net.netstring import NetstringProtocol, LENGTH
import unittest
import mock


class TestNetstringProtocol(unittest.TestCase):
    """
    Ensures the Netstring Protocol class works as expected.
    """

    def test_init(self):
        """
        Ensure the object is instantiated with the expected attributes.
        """
        p = NetstringProtocol('fake_connector', 'fake_node')
        self.assertEqual('fake_connector', p._connector)
        self.assertEqual('fake_node', p._node)
        length = 1024 * 1024 * 12
        self.assertEqual(p.MAX_LENGTH, length)
        self.assertEqual(p._reader_state, LENGTH)
        self.assertEqual(p._reader_length, 0)

    def test_connection_made(self):
        """
        Ensure the transport is correctly set when a connection is made.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made('abc')
        self.assertEqual('abc', p.transport)

    def test_data_received(self):
        """
        Ensure that good data results in the expected results:

        * No errors.
        * The correct call to string received.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello world,'.encode('utf-8'))
        p.string_received.assert_called_once_with('hello world')

    def test_string_received(self):
        """
        Ensure the string_received method works as expected.
        """
        transport = mock.MagicMock()
        transport.get_extra_info = mock.MagicMock(return_value='192.168.0.1')
        connector = mock.MagicMock()
        connector.receive = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.string_received('hello world')
        connector.receive.assert_called_once_with('hello world', '192.168.0.1',
                                                  node, p)

    def test_data_received_more_data(self):
        """
        Ensure that sequences of netstring from the remote peer are correctly
        handled.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello world,'.encode('utf-8'))
        p.data_received('11:hello world,'.encode('utf-8'))
        self.assertEqual(2, p.string_received.call_count)

    def test_data_received_in_chunks(self):
        """
        Ensure the netstring is re-constructed correctly if it is received
        over several calls to data_received (i.e. ensure the FSM is working).
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('11:hello '.encode('utf-8'))
        p.data_received('world,'.encode('utf-8'))
        p.string_received.assert_called_once_with('hello world')

    def test_data_received_containing_weird_unicode(self):
        """
        Ensure the netstring is re-constructed correctly if it contains weird
        unicode characters and a non-obvious length.
        """
        p = NetstringProtocol('foo', 'bar')
        p.connection_made(mock.MagicMock())
        p.string_received = mock.MagicMock()
        p.data_received('15:zɐq ɹɐq ooɟ,'.encode('utf-8'))
        p.string_received.assert_called_once_with('zɐq ɹɐq ooɟ')

    def test_data_received_bad_end_character(self):
        """
        If the netstring does not terminate with a comma ensure that it is
        handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('11:hello world@'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_bad_length(self):
        """
        If the netstring does not start with an integer defining the length
        of the message then ensure the problem is handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('foo:hello world,'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_length_too_long(self):
        """
        If the netstring is expected to be too long then ensure the problem is
        handled correctly.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.data_received('999999999999999999:hello world,'.encode('utf-8'))
        self.assertEqual(1, transport.close.call_count)

    def test_data_received_in_bad_state(self):
        """
        Ensure the correct RuntimeError is called if the state of the FSM is
        invalid.
        """
        transport = mock.MagicMock()
        transport.close = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p._reader_state = 4
        with self.assertRaises(RuntimeError):
            p.data_received('11:hello world@'.encode('utf-8'))

    def test_send_string(self):
        """
        Ensure the raw string form of the message is correctly turned into a
        valid netstring.
        """
        transport = mock.MagicMock()
        transport.write = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.send_string('foo bar baz')
        transport.write.assert_called_once_with(b'11:foo bar baz,')

    def test_send_utf8_string_with_correct_length(self):
        """
        Ensure the raw string containing weird unicode chars is correctly
        turned into a valid netstring with the correct length.
        """
        transport = mock.MagicMock()
        transport.write = mock.MagicMock()
        connector = mock.MagicMock()
        node = mock.MagicMock()
        p = NetstringProtocol(connector, node)
        p.connection_made(transport)
        p.send_string('zɐq ɹɐq ooɟ')
        length = len('zɐq ɹɐq ooɟ'.encode('utf-8'))
        expected = '%d:zɐq ɹɐq ooɟ,' % length
        transport.write.assert_called_once_with(expected.encode('utf-8'))


class TestNetstringConnector:
    """
    Checks the NetstringConnector class works as expected.
    """

    def test_init(self):
        """
        Check the class instantiates as expected.
        """
        nc = NetstringConnector()
        self.assertEqual(nc._connections, {})
