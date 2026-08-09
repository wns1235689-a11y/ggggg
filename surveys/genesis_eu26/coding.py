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


def _hit(text, keys):
    """단어 경계 매칭(F5: 'spa'가 Spain/space에 걸리는 substring 오매칭 차단)."""
    t = (text or "").lower()
    for k in keys:
        if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t):
            return True
    return False


def magma_depth(verbatim):
    """마그마 회상 원문 → 'specific'|'vague'|'echo'|'none'.
    echo(P1-08) = 질문이 제시한 어휘(Le Mans/WEC/racing)만 반복 — 지식 아닌 반향."""
    if _hit(verbatim, C.MAGMA_SPECIFIC_KEYS):
        return "specific"
    if _hit(verbatim, C.MAGMA_VAGUE_KEYS):
        return "vague"
    if _hit(verbatim, C.MAGMA_ECHO_KEYS):
        return "echo"
    return "none"
