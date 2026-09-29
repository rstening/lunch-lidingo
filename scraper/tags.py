"""Guess a dish's tag (kött, fisk, veg or soppa) from Swedish menu words.

Used only for dishes where the restaurant gives no tag of its own. Rules:
soup always wins, an explicit "veg..." word wins next, and otherwise the
first mentioned main ingredient decides, since menus lead with it. A dish
with no known word gets no tag at all.
"""
import re
from typing import List

# Stems match inside compounds (fiskgryta, kycklingklubba), so each entry
# is anchored where a bare stem would also hit unrelated words.
_FISH = (
    r"fisk|havets|lax|torsk|kolja|röding|\bsej|\bgös|abborre|gädda|\bsill|strömming|makrill|spätta"
    r"|rödtunga|\blånga|flundra|piggvar|havskatt|marulk|sjötunga|\bsik|räk|kräft"
    r"|skaldjur|mussl|krabb|hummer|ostron|scampi|calamari|kalamari"
)
_MEAT = (
    r"(?<!vego)korv|fläsk|kyckling|chicken|kalkon|kalv|lamm|\bbiff|steak|flankstek"
    r"|ryggbiff|rostbiff|lövbiff|pannbiff|entrec[oô]te|oxfilé|oxbringa|oxkind|högrev"
    r"|nöt(?:kött|färs|stek|schnitzel|bringa|gryta|bog|filé|rulle)|kött(?!fri)"
    r"|bacon|skinka|pancetta|isterband|porchetta|chorizo|salsiccia|merguez"
    r"|\bpork\b|kassler|karré|revben|kotlett|wallenbergare|wienerschnitzel"
    r"|kebab|gyros|\bcarne\b|bolognese|\bank(?:a|bröst|lår)|vilt|älg|hjort|rådjur"
    r"|ren(?:skav|stek|kött)|blodpudding|coq au vin"
)
_VEG = (
    r"tofu|paneer|halloumi|falafel|\blins|kikärt|quorn|tempeh|seitan|oumph"
    r"|sojafärs|bönbiff|svampbiff"
)
_VEG_WORD = re.compile(r"\bveg", re.IGNORECASE)
_SOUP = re.compile(r"soppa", re.IGNORECASE)
_MAIN = [("fisk", re.compile(_FISH, re.IGNORECASE)),
         ("kött", re.compile(_MEAT, re.IGNORECASE)),
         ("veg", re.compile(_VEG, re.IGNORECASE))]


def guess_tags(name: str) -> List[str]:
    if _SOUP.search(name):
        return ["soppa"]
    if _VEG_WORD.search(name):
        return ["veg"]
    hits = []
    for tag, pattern in _MAIN:
        m = pattern.search(name)
        if m:
            hits.append((m.start(), tag))
    if not hits:
        return []
    return [min(hits)[1]]
