from bruteforce import BruteforcePlugin


def test_bruteforce_init():
    b = BruteforcePlugin()
    assert b.search_wikipedia in b._raw_listeners["before_choose_candidate"]
