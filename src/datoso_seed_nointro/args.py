from datoso.configuration import config


def seed_args(parser):
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument('-vi', '--visible', action='store_const', help='Run with browser visible',
                          dest='headless', const=False)
    headless.add_argument('-hl', '--headless', action='store_const', help='Run with browser headless (default)',
                          dest='headless', const=True)
    parser.set_defaults(headless=None)

def post_parser(args):
    if getattr(args, 'headless', None) is not None:
        config.set('NOINTRO', 'headless', str(args.headless))

def init_config():
    if not config.has_section('NOINTRO'):
        config['NOINTRO'] = {
            'headless': 'True',
            'include_aftermarket': 'True',
            'include_non_game': 'False',
            'include_redump_custom': 'False',
            'include_redump_bios': 'False',
        }
