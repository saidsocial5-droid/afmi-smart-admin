"""Structures communes du pipeline."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

LOW_CONFIDENCE = 75.0


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 100.0
    page: int = 0

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return max(1.0, self.y1 - self.y0)


@dataclass
class ExtractedLine:
    date: Optional[str]            # ISO yyyy-mm-dd
    value_date: Optional[str]
    label: str
    reference: str
    debit: int                     # centimes
    credit: int
    confidence: Dict[str, float] = field(default_factory=dict)
    page: int = 0
    y: float = 0.0                 # position sur la page (pour surligner dans l'écran de validation)

    def low_fields(self) -> List[str]:
        return [k for k, v in self.confidence.items() if v < LOW_CONFIDENCE]


@dataclass
class ExtractedStatement:
    bank_id: str = ""
    bank_name: str = ""
    rib: str = ""
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening: Optional[int] = None
    closing: Optional[int] = None
    currency: str = "MAD"
    lines: List[ExtractedLine] = field(default_factory=list)
    confidence: Dict[str, float] = field(default_factory=dict)
    engine: str = ""               # "pdf-natif", "tesseract", "ia:<moteur>", "tableur"
    pages: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def movement(self) -> int:
        return sum(l.credit - l.debit for l in self.lines)

    def balance_ok(self) -> Optional[bool]:
        if self.opening is None or self.closing is None:
            return None
        return self.opening + self.movement == self.closing
