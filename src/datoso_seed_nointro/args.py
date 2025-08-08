"""Argument parser for No-Intro seed."""
from argparse import ArgumentParser, Namespace

from datoso.configuration import config
from datoso_seed_nointro.common import categories


def seed_args(parser: ArgumentParser) -> ArgumentParser:
    """Add seed arguments to the parser."""
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument('-vi', '--visible', action='store_const', help='Run with browser visible',
                          dest='headless', const=False)
    headless.add_argument('-hl', '--headless', action='store_const', help='Run with browser headless (default)',
                          dest='headless', const=True)
    parser.add_argument('-i', '--include', nargs='+',
                        choices=categories.keys(), help='Include categories not configured')
    parser.add_argument('-e', '--exclude', nargs='+',
                        choices=categories.keys(), help='Exclude categories')

    parser.set_defaults(headless=None)
    return parser

def post_parser(args: Namespace) -> None:
    """Post parser actions."""
    if getattr(args, 'headless', None) is not None:
        config.set('NOINTRO', 'headless', str(args.headless))
    if getattr(args, 'include', None) is not None:
        config.set('NOINTRO', 'include_categories', ','.join(args.include))
    if getattr(args, 'exclude', None) is not None:
        config.set('NOINTRO', 'exclude_categories', ','.join(args.exclude))

def init_config() -> None:
    """Initialize the configuration."""
    default_values = {
        'headless': 'True',
        'include_categories': '',
        'exclude_categories': '',
    }
    if not config.has_section('NOINTRO'):
        config['NOINTRO'] = default_values
    for key, value in default_values.items():
        if not config.has_option('NOINTRO', key):
            config.set('NOINTRO', key, str(value))
