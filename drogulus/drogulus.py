# -*- coding: utf-8 -*-
"""
Entry point for running the drogulus and related utilities from the command
line.
"""
from .version import get_version
from cliff.app import App
from cliff.commandmanager import CommandManager
import sys


class DrogulusCommand(App):
    """
    Encapsulates the drogulus command for configuring and running the
    drogulus peer-to-peer data store.
    """

    def __init__(self):
        description = ' '.join(['The drogulus - a peer-to-peer data store',
                                'built for simplicity, security, openness',
                                'and fun.'])
        super(DrogulusCommand, self).__init__(
            description=description,
            version=get_version(),
            command_manager=CommandManager('drogulus.commands'),
        )

    def clean_up(self, cmd, result, err):
        """
        If something went wrong, best to feedback to the user. :-(
        """
        if err:
            print('There was a problem:')
            print(err)
            sys.exit(1)


def main(argv=sys.argv[1:]):
    if not (sys.version_info[0] == 3 and sys.version_info[1] >= 3):
        print('Need Python 3.3+ to run.')
        return 1
    else:
        drogulus = DrogulusCommand()
        return drogulus.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
