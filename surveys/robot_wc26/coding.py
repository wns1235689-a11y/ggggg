# -*- coding: utf-8 -*-
"""Q2/프로브 verbatim → 코드 판정 (프로토콜 §6 + DESC 부록 코드).

현장 규칙과 동일 정신: 최초 발화 우선(복수 기업 나열 시), 원문 보존은 호출자 몫.
DESC(이름 없는 BD 서술 식별)는 사전등록 부록으로 제안된 밤-코딩 신설 코드.
"""
import re

import config as C


def _hit(text, keys):
    t = text.lower()
    for k in keys:
        if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t):
            return True
    return False


def _first_company(text):
    """문장 내 최초 등장 기업(프로토콜 '최초 발화 우선')."""
    t = text.lower()
    best = None
    for name, keys in C.COMPANY_PATTERNS:
        for k in keys:
            m = re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", t)
            if m and (best is None or m.start() < best[1]):
                best = (name, m.start())
    return best[0] if best else None


def code_q2(text):
    """→ 'A1'|'A2'|'A3'|'G'|'W-<NAME>'|'DESC'|'DK'|'UNCODED'

    동결 §6 규칙 준수(판정단 P1-03/F3 반영): 복수 기업 나열은 **최초 발화 우선**.
    A3는 분기C 취지대로 '현대·BD가 모두 등장하고 그보다 앞선 타사 발화가 없는 경우'만.
    (예: 'Tesla? Or Hyundai maybe?' → W-TESLA — 현장 밤 코딩과 동일)
    """
    t = (text or "").strip()
    if not t:
        return "DK"
    first = _first_company(t)
    hy = _hit(t, dict(C.COMPANY_PATTERNS)["HYUNDAI"])
    bd = _hit(t, dict(C.COMPANY_PATTERNS)["BOSTON"])
    if first in ("HYUNDAI", "BOSTON"):
        if hy and bd:
            return "A3"
        return "A1" if first == "HYUNDAI" else "A2"
    if first == "GENESIS":
        return "G"
    if first:
        return f"W-{first}"
    if _hit(t, C.DESC_KEYS):
        return "DESC"
    if _hit(t, C.DK_KEYS) or t.rstrip("?").strip() == "":
        return "DK"
    return "UNCODED"


def code_probe_a(text):
    """분기A(BD 소유주) → 'HYUNDAI'|'GOOGLE_STALE'|'SOFTBANK_STALE'|'DK'|'OTHER'"""
    t = (text or "").strip()
    if _hit(t, dict(C.COMPANY_PATTERNS)["HYUNDAI"]):
        return "HYUNDAI"
    if _hit(t, dict(C.COMPANY_PATTERNS)["GOOGLE"]):
        return "GOOGLE_STALE"
    if _hit(t, dict(C.COMPANY_PATTERNS)["SOFTBANK"]):
        return "SOFTBANK_STALE"
    if _hit(t, C.DK_KEYS) or not t:
        return "DK"
    return "OTHER"


def code_probe_b(text):
    """분기B(현대 명명자에게 로봇 제작사명) → 'BOSTON'|'DK'|'OTHER'"""
    t = (text or "").strip()
    if _hit(t, dict(C.COMPANY_PATTERNS)["BOSTON"]):
        return "BOSTON"
    if _hit(t, C.DK_KEYS) or not t:
        return "DK"
    return "OTHER"
