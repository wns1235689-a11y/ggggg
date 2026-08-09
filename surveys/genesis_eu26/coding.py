# -*- coding: utf-8 -*-
"""제네시스 설문 코딩 — Q1 비보조 브랜드 정규화 · 마그마 회상 깊이 판정."""
import re

import config as C


def norm_brands(q1_line):
    """비보조 한 줄("BMW, Mercedes, maybe Audi") → 정규화 브랜드 리스트(언급 순서 보존)."""
    t = (q1_line or "").lower()
    found = []
    for canon, keys in C.BRAND_ALIASES.items():
        best = None
        for k in keys:
            m = re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t)
            if m and (best is None or m.start() < best):
                best = m.start()
        if best is not None:
            found.append((best, canon))
    return [c for _, c in sorted(found)]


def genesis_position(q1_line):
    """Genesis 언급 순번(1-base) | None."""
    brands = norm_brands(q1_line)
    return brands.index("GENESIS") + 1 if "GENESIS" in brands else None


def magma_depth(verbatim):
    """마그마 회상 원문 → 'specific'|'vague'|'none'."""
    t = (verbatim or "").lower()
    for k in C.MAGMA_SPECIFIC_KEYS:
        if k in t:
            return "specific"
    for k in C.MAGMA_VAGUE_KEYS:
        if k in t:
            return "vague"
    return "none"
