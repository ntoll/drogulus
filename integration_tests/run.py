import os
import uuid
import tempfile
from subprocess import Popen


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


def run_tests(port, logfile):
    """
    Stuff
    """
    pass


if __name__ == '__main__':
    logfile = get_logfile()
    node = start_node(NODE_LISTENING_PORT, logfile)
    run_tests(NODE_LISTENING_PORT, logfile)
    node.terminate()
