"""3K (SPEC_3_mvp.md 12.20, Julius's decision 2 of 2026-11-08): a plate-weight model, statistics on measured chain items.

`scripts/plate_model.py` fits a ridge regression from an item's name words, its dish family and its kids flag to the log of its measured serving weight, on MenuStat's
items and the chain sheets, validated on held-out restaurants, and writes `recipes/plate_model.json`: the coefficients, the vocabulary, and per family the quantiles of the
held-out residuals. At run time (`PlateModel.sample`) a P2 dish's plate weight is drawn as exp(prediction + a residual drawn from its family's held-out quantiles), kept
only inside the row's approved range. The LLM writes nothing here; every coefficient is a fitted number over measured items with their sources in the training file.
`live` in the JSON records whether the held-out check met the switch rule (coverage at least the family range's, intervals narrower); MenuRunner follows it unless the
config says otherwise. Pure Python: Roli's environment has no numpy.
"""

from __future__ import annotations

import bisect
import json
import math
import random
import re
from pathlib import Path

from .relevance import singular

DEFAULT_PATH = Path(__file__).resolve().parent / "plate_model.json"
TOKEN = re.compile(r"[a-z]{3,}")
KIDS_WORDS = re.compile(r"\b(kids?|children|ni[nñ]os|little ones|junior)\b", re.I)


def tokens(name: str) -> list[str]:
    return sorted({singular(t) for t in TOKEN.findall(name.lower())})


def features(name: str, family: str | None, kids: bool, vocabulary: set[str] | None = None) -> list[str]:
    """The feature names of one item: word:<token> for vocabulary words, fam:<family>, kids."""
    out = [f"word:{t}" for t in tokens(name) if vocabulary is None or f"word:{t}" in vocabulary]
    out.append(f"fam:{family or 'none'}")
    if kids:
        out.append("kids")
    return out


class PlateModel:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.intercept = float(data["intercept"])
        self.coef = {k: float(v) for k, v in data["coef"].items()}
        self.vocabulary = set(k for k in self.coef if k.startswith("word:"))
        self.families = data.get("families", {})
        self.pooled = data.get("pooled_residual_quantiles") or []
        self.live = bool(data.get("live", False))
        self.version = data.get("version", "")

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> "PlateModel | None":
        p = Path(path)
        if not p.exists():
            return None
        return cls(json.loads(p.read_text(encoding="utf-8")))

    def predict_log(self, name: str, family: str | None, kids: bool = False) -> float:
        return self.intercept + sum(self.coef.get(f, 0.0) for f in features(name, family, kids, self.vocabulary))

    def residual_quantiles(self, family: str | None) -> list[float]:
        fam = self.families.get(family or "none")
        if fam and fam.get("residual_quantiles") and fam.get("n", 0) >= 30:
            return fam["residual_quantiles"]
        return self.pooled

    def interval(self, name: str, family: str | None, kids: bool = False, q_low: float = 0.10, q_high: float = 0.90) -> tuple[float, float]:
        """exp(prediction + the residual quantiles): the model's own middle band in grams."""
        mu = self.predict_log(name, family, kids)
        qs = self.residual_quantiles(family)
        lo = _q(qs, q_low) if qs else 0.0
        hi = _q(qs, q_high) if qs else 0.0
        return math.exp(mu + lo), math.exp(mu + hi)

    def sample(self, rng: random.Random, name: str, section: str, family: str | None, low: float, high: float, tries: int = 50) -> float | None:
        """One plate weight in grams inside [low, high] (the approved row range): exp(prediction + a residual drawn by inverse CDF); None when fifty draws all fall outside."""
        qs = self.residual_quantiles(family)
        if not qs:
            return None
        mu = self.predict_log(name, family, bool(KIDS_WORDS.search(section or "")))
        for _ in range(tries):
            u = rng.random()
            w = math.exp(mu + _q(qs, u))
            if low <= w <= high:
                return w
        return None


def _q(qs: list[float], u: float) -> float:
    """Inverse CDF over quantiles stored at 0, 0.05, ..., 1.0 (21 values), linear between them."""
    if not qs:
        return 0.0
    pos = u * (len(qs) - 1)
    i = min(int(pos), len(qs) - 2)
    return qs[i] + (qs[i + 1] - qs[i]) * (pos - i)
