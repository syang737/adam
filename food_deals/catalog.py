import re

_MARKS = re.compile(r"[®™©]")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def item_key(name: str) -> str:
    """Canonical key for matching one chain's item across its stores.

    "Crunchwrap Supreme®" -> "crunchwrap supreme". Deliberately exact after
    normalisation: "Crunchwrap Supreme® Combo" and "Black Bean Crunchwrap
    Supreme®" are different products and must not match.
    """
    return _NON_WORD.sub(" ", _MARKS.sub("", name).lower()).strip()


def chain_key(name: str) -> str:
    return item_key(name)
