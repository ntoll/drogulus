# -*- coding: utf-8 -*-
"""
Defines the command for creating whoami data to self-identify the owner of a
public key in the drogulus DHT.
"""
from cliff.command import Command
from .utils import data_dir
import json
import os


class WhoAmI(Command):
    """
    Generates a fragment of json to be used as the value to self-identify the
    owner of a public key in the drogulus DHT.
    """

    contact_fields = ['Name', 'Nickname', 'Organizational affiliation',
                      'Website', 'Contact information (e.g. email)',
                      'Biography', 'Miscellaneous notes']
    """
    This list of contact fields defines the field names used to reference data
    in the whoami JSON file. They're a bit arbitrary, but vaguely based upon
    a small basic subset of fields used by vcard (see rfc2426).
    """

    def get_description(self):
        return ' '.join(['Generates a whoami data structure to self-identify',
                        'a user.'])

    def take_action(self, parsed_args):
        """
        Interrogates the user for details of who they are so their public key
        is associated with some sort of contact details.
        """
        whoami = {}
        print('Create a whoami profile.')
        print('(Blank fields will be left out of the profile.)')
        while True:
            for field in self.contact_fields:
                val = str(input('{}: '.format(field))).strip()
                if val:
                    whoami[field] = val
            print('\nPlease check:')
            for k, v in iter(whoami.items()):
                print('{}: {}'.format(k, v))
            check = input('OK [y/n]?')
            if check.lower() == 'y':
                break
        output_file = os.path.join(data_dir(), 'whoami.json')
        with open(output_file, 'w') as f:
            json.dump(whoami, f)
        print('Written details to: {}'.format(output_file))
