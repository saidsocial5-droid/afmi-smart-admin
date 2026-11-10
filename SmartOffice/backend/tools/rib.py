"""RIB marocain : 24 chiffres = banque (3) + localité (3) + compte (16) + clé (2).

Clé = 97 - ((22 premiers chiffres x 100) mod 97). Même règle que Core/Finance/Rib.cs ; les deux
implémentations sont vérifiées sur les mêmes vecteurs (SharedTestCases/rib.json).
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RibCheck:
    is_well_formed: bool
    is_key_valid: bool
    normalized: str
    expected_key: Optional[int] = None

    @property
    def is_valid(self) -> bool:
        return self.is_well_formed and self.is_key_valid


def normalize(value: Optional[str]) -> str:
    if not value or not value.strip():
        return ""
    if re.search(r"[^\d \-. ]", value):
        return value.strip()
    return re.sub(r"\D", "", value)


def compute_key(first_22_digits: str) -> int:
    if len(first_22_digits) != 22 or not first_22_digits.isdigit():
        raise ValueError("22 chiffres attendus (banque, localité, compte).")
    return 97 - (int(first_22_digits) * 100) % 97


def check(value: Optional[str]) -> RibCheck:
    rib = normalize(value)
    if len(rib) != 24 or not (rib.isascii() and rib.isdigit()):
        return RibCheck(False, False, rib)
    expected = compute_key(rib[:22])
    return RibCheck(True, expected == int(rib[22:]), rib, expected)
