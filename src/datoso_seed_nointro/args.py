"""Argument parser for No-Intro seed."""
from argparse import ArgumentParser, Namespace

from datoso.configuration import config


def seed_args(parser: ArgumentParser) -> ArgumentParser:
    """Add seed arguments to the parser."""
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument('-vi', '--visible', action='store_const', help='Run with browser visible',
                          dest='headless', const=False)
    headless.add_argument('-hl', '--headless', action='store_const', help='Run with browser headless (default)',
                          dest='headless', const=True)
    parser.set_defaults(headless=None)
    return parser

def post_parser(args: Namespace) -> None:
    """Post parser actions."""
    if getattr(args, 'headless', None) is not None:
        config.set('NOINTRO', 'headless', str(args.headless))

def init_config() -> None:
    """Initialize the configuration."""
    if not config.has_section('NOINTRO'):
        config['NOINTRO'] = {
            'headless': 'True',
            'include_aftermarket': 'True',
            'include_non_game': 'False',
            'include_redump_custom': 'False',
            'include_redump_bios': 'False',
        }
