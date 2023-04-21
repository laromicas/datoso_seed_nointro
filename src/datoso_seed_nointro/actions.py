from datoso_seed_nointro.dats import NoIntroDat

actions = {
    '{dat_origin}': [
        {
            'action': 'LoadDatFile',
            '_class': NoIntroDat
        },
        {
            'action': 'DeleteOld'
        },
        {
            'action': 'Copy',
            'folder': '{dat_destination}'
        },
        {
            'action': 'SaveToDatabase'
        }
    ]
}

def get_actions():
    return actions