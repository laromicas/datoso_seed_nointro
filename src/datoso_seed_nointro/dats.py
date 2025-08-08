"""NoIntro Dat classes."""
import os
import re

from datoso.configuration import config
from datoso.helpers import is_date
from datoso.repositories.dat_file import ClrMameProDatFile, XMLDatFile


class NoIntroDat(XMLDatFile):
    """NoIntro Dat class."""

    seed: str = 'nointro'

    def initial_parse(self) -> list:
        """Parse the dat file."""
        # pylint: disable=R0801
        name = self.name

        suffixes = re.findall(r'\(.*?\)', self.full_name)
        name = name.replace(' '.join(suffixes), '').strip()
        name_array = name.split(' - ')

        if suffixes:
            suffixes = [x[1:-1] for x in suffixes]

        if name_array[0] == 'Non-Redump':
            suffixes.append('ExtraDiscs')
            name_array.pop(0)
        elif name_array[0] == 'Unofficial':
            name_array.pop(0)
            if 'Magazine Scans' not in name:
                suffixes.append('UnofficialDiscs')

        prefixes = []
        if name_array[0] == 'Source Code':
            prefixes.append(name_array.pop(0))
            self.modifier = 'Source Code'
        union = config.get('GENERAL', 'UnionCharacter')
        expected_name_position = 2
        if len(name_array) > expected_name_position:
            name_array[1] = f'{name_array[1]} {union} {name_array.pop()}'

        if len(name_array) == 1:
            name_array.insert(0, None)

        company, system = name_array
        self.company = company
        self.system = system
        if "(DoM Version)" in system:
            self.system = system.split(' - ')[0]
            suffixes = ['BIOS Images', 'DoM Version']
        else:
            self.system = system

        if suffixes:
            self.suffix = os.path.join(*suffixes) # noqa: PTH118

        self.suffixes = suffixes
        find_system = self.overrides()
        self.extra_configs(find_system)

        if self.modifier or self.system_type:
            self.prefix = config.get('PREFIXES', self.modifier or self.system_type, fallback='')
        else:
            self.prefix = None

        return [self.prefix, self.company, self.system, self.suffix, self.get_date()]


    def get_date(self) -> str:
        """Get the date from the dat file."""
        if self.date:
            return self.date
        if self.version:
            self.date = self.version
        if self.file:
            result = re.findall(r'\(.*?\)', str(self.file))
            self.date = result[len(result)-1][1:-1]
        return self.date if is_date(self.date) else None


class NoIntroClrMameDat(ClrMameProDatFile):
    """NoIntro Dat class."""

    repo: str = 'nointro'

    def initial_parse(self) -> list:
        """Parse the dat file."""
        # pylint: disable=R0801
        name = self.name

        suffixes = re.findall(r'\(.*?\)', self.full_name)
        name = name.replace(' '.join(suffixes), '').strip()
        name_array = name.split(' - ')

        self.modifier = name_array.pop()

        company, system = name_array

        self.company = company
        self.system = system
        self.suffix = None

        self.suffixes = suffixes

        self.prefix = config['PREFIXES'].get(self.modifier or self.system_type, '')

        return [self.prefix, self.company, self.system, self.suffix, self.get_date()]

    def get_date(self) -> str:
        """Get the date from the dat file."""
        self.date = self.version
        return self.version
