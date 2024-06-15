"""Actions for the No-Intro seed."""
from datoso_seed_nointro.dats import NoIntroDat

actions = {
    '{dat_origin}': [
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
    return actions
