"""Actions for the No-Intro seed."""
from datoso_seed_nointro.common import get_categories
from datoso_seed_nointro.dats import NoIntroDat

actions = {
    '{dat_origin}/{folder}': [
        {
            'action': 'LoadDatFile',
            '_class': NoIntroDat,
        },
        {
            'action': 'DeleteOld',
            'folder': '{dat_destination}',
        },
        {
            'action': 'Copy',
            'folder': '{dat_destination}',
        },
        {
            'action': 'SaveToDatabase',
        },
    ],
}



def get_actions() -> dict:
    """Get the actions dictionary."""
    folders = ['No-Intro'] + [metadata['folder'] for _, metadata in get_categories()]
    new_actions = {}
    for folder in folders:
        folder_name = '{dat_origin}/' + folder
        new_actions[folder_name] = actions['{dat_origin}/{folder}']
    return new_actions
