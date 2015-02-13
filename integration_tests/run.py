import os
import sys
import time
import uuid
import tempfile
import json
import requests
import rsa
from subprocess import Popen
from uuid import uuid4
from hashlib import sha512
sys.path.append(os.path.join('..', 'drogulus'))
from drogulus.dht.messages import from_dict
from drogulus.dht.crypto import (get_signed_item, construct_key, get_seal,
                                 check_seal)
from drogulus.version import get_version
from start_node import PUBLIC_KEY as REMOTE_NODE_PUBLIC_KEY


NODE_LISTENING_PORT = 8888


def get_logfile():
    """
    Returns a string identifying the temporary location of a randomly named
    log file to use and tail during the integration tests.
    """
    logfilename = ''.join(['drogulus_test', str(uuid.uuid4().hex), '.log'])
    return os.path.join(tempfile.gettempdir(), logfilename)


def start_node(port, logfile):
    """
    Runs the script to start a local node to test in a different process. The
    node will listen on the referenced port and log to the file at the
    referenced path.

    Returns an instance of Popen that should be terminated when the tests
    finish.
    """
    return Popen(['python', os.path.join('integration_tests', 'start_node.py'),
                 str(port), logfile])


def send_message(port, msg):
    """
    Sends a JSON message to the node and returns its reply.
    """
    return requests.post("http://localhost:{}/".format(port), json.dumps(msg),
                         headers={'content-type': 'application/json'})


def get_keypair():
    """
    Returns a (private, public) key pair as two strings encoded as pkcs1.
    """
    public, private = rsa.newkeys(1024)
    return (private.save_pkcs1().decode('ascii'),
            public.save_pkcs1().decode('ascii'))


def seal_message(msg_type, msg_dict, private_key):
    """
    Returns a version of the message containing the cryptographic seal and
    message type.
    """
    seal = get_seal(msg_dict, private_key)
    msg_dict['seal'] = seal
    msg_dict['message'] = msg_type
    return msg_dict


def send_store(port, version, public_key, private_key):
    """
    Sends and "store" message to the test node and check's the reply.
    """
    print('Sending "store" message...')
    item = get_signed_item('item_name', "the item's value", public_key,
                           private_key)
    item['uuid'] = str(uuid4())
    item['recipient'] = REMOTE_NODE_PUBLIC_KEY
    item['sender'] = public_key
    item['reply_port'] = 1908
    item['version'] = version
    msg = seal_message('store', item, private_key)
    result = send_message(port, msg)
    assert result.status_code == 200
    reply = result.json()
    assert reply['uuid'] == item['uuid']
    assert reply['sender'] == REMOTE_NODE_PUBLIC_KEY
    assert reply['recipient'] == public_key
    assert reply['message'] == 'ok'
    assert reply['reply_port'] == port
    assert reply['version'] == version
    assert 'seal' in reply
    assert check_seal(from_dict(reply))


def send_find_node(port, version, public_key, private_key):
    """
    Ensures that a "findnode" message is sent to the test node and the
    reply is checked.
    """
    print('Sending "findnode" message...')
    item = {
        'uuid': str(uuid.uuid4()),
        'recipient': REMOTE_NODE_PUBLIC_KEY,
        'sender': public_key,
        'reply_port': 1908,
        'version': version,
        'key': sha512('a key'.encode('utf-8')).hexdigest(),
    }
    msg = seal_message('findnode', item, private_key)
    result = send_message(port, msg)
    assert result.status_code == 200
    reply = result.json()
    assert reply['uuid'] == item['uuid']
    assert reply['sender'] == REMOTE_NODE_PUBLIC_KEY
    assert reply['recipient'] == public_key
    assert reply['message'] == 'nodes'
    assert reply['reply_port'] == port
    assert reply['version'] == version
    assert 'nodes' in reply
    assert isinstance(reply['nodes'], list)
    assert len(reply['nodes']) == 1  # the node only knows about us!
    assert 'seal' in reply
    assert check_seal(from_dict(reply))


def send_find_value_unknown(port, version, public_key, private_key):
    """
    Ensures that a "findvalue" message for a non-existent key is sent to the
    test node and the reply is checked.
    """
    print('Sending "findvalue" message with no known key...')
    item = {
        'uuid': str(uuid.uuid4()),
        'recipient': REMOTE_NODE_PUBLIC_KEY,
        'sender': public_key,
        'reply_port': 1908,
        'version': version,
        'key': sha512('an un-findable key'.encode('utf-8')).hexdigest(),
    }
    msg = seal_message('findvalue', item, private_key)
    result = send_message(port, msg)
    assert result.status_code == 200
    reply = result.json()
    assert reply['uuid'] == item['uuid']
    assert reply['sender'] == REMOTE_NODE_PUBLIC_KEY
    assert reply['recipient'] == public_key
    assert reply['message'] == 'nodes'
    assert reply['reply_port'] == port
    assert reply['version'] == version
    assert 'nodes' in reply
    assert isinstance(reply['nodes'], list)
    assert len(reply['nodes']) == 1  # the node only knows about us!
    assert 'seal' in reply
    assert check_seal(from_dict(reply))


def send_find_value_known(port, version, public_key, private_key):
    """
    Ensures that a "findvalue" message for an existing  key is sent to the
    test node and the reply is checked.
    """
    item = get_signed_item('item_name', "the item's value", public_key,
                           private_key)
    signature = item['signature']
    item['uuid'] = str(uuid4())
    item['recipient'] = REMOTE_NODE_PUBLIC_KEY
    item['sender'] = public_key
    item['reply_port'] = 1908
    item['version'] = version
    msg = seal_message('store', item, private_key)
    result = send_message(port, msg)
    assert result.status_code == 200
    print('Sending "findvalue" message for existing key...')
    item = {
        'uuid': str(uuid.uuid4()),
        'recipient': REMOTE_NODE_PUBLIC_KEY,
        'sender': public_key,
        'reply_port': 1908,
        'version': version,
        'key': construct_key(public_key, 'item_name'),
    }
    msg = seal_message('findvalue', item, private_key)
    result = send_message(port, msg)
    assert result.status_code == 200
    reply = result.json()
    assert reply['uuid'] == item['uuid']
    assert reply['sender'] == REMOTE_NODE_PUBLIC_KEY
    assert reply['recipient'] == public_key
    assert reply['message'] == 'value'
    assert reply['reply_port'] == port
    assert reply['version'] == version
    assert reply['name'] == 'item_name'
    assert reply['value'] == "the item's value"
    assert reply['key'] == construct_key(public_key, 'item_name')
    assert reply['public_key'] == public_key
    assert reply['signature'] == signature
    assert reply['expires'] == 0.0
    assert reply['created_with'] == version
    assert isinstance(reply['timestamp'], float)
    assert 'seal' in reply
    assert check_seal(from_dict(reply))


def send_get(port, version, public_key, private_key):
    """
    Ensures that a "findvalue" message for an existing  key is sent to the
    test node and the reply is checked.
    """
    print('Sending GET...')
    result = requests.get("http://localhost:{}/foo".format(port))
    print(result)
    assert result.status_code == 200


def run_tests(port, logfile):
    """
    Send each sort of message to the node and check each response is as
    expected.
    """
    private_key, public_key = get_keypair()
    version = get_version()
    checks = [send_store, send_find_node, send_find_value_unknown,
              send_find_value_known, send_get]
    fails = 0
    for test in checks:
        try:
            test(port, version, public_key, private_key)
            print('OK')
        except Exception as ex:
            print('FAIL')
            print(ex)
            fails += 1
    return fails


if __name__ == '__main__':
    logfile = get_logfile()
    print('Starting local node on port {}'.format(NODE_LISTENING_PORT))
    print('(Logging to {})'.format(logfile))
    node = start_node(NODE_LISTENING_PORT, logfile)
    time.sleep(1)
    fails = 0
    try:
        print('Starting tests...')
        fails = run_tests(NODE_LISTENING_PORT, logfile)
    finally:
        print('Shutting down local node...')
        node.terminate()
    sys.exit(fails)
