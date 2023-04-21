from datoso_seed_nointro.dats import NoIntroDat

rules = [
    {
        "name": "No-Intro DAT",
        "_class": NoIntroDat,
        "seed": "nointro",
        "priority": 50,
        "rules": [
            {
                "key": "url",
                "operator": "contains",
                "value": "www.no-intro.org"
            },
            {
                "key": "homepage",
                "operator": "eq",
                "value": "No-Intro"
            }
        ]
    }
]


def get_rules():
    return rules