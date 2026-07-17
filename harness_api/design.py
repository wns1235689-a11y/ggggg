# -*- coding: utf-8 -*-
"""설계 뷰어(읽기 전용) 데이터 — 현행 v2.3 문항·보기·latent·ANCHOR_PRIORS를 코드에서 파싱.
엔진 코드는 임포트/정적 파싱만 하며 수정하지 않는다(SPEC §5.5·§6.4).
"""
import os
import re

from . import REPO_ROOT
import sim.config as C

WF_V23 = os.path.join(REPO_ROOT, "wf_vs_v23.js")


def latent_specs():
    """sim.config.LATENT_SPECS(21개) → {name: {mu, sd}} (직접 임포트, 파싱 없음)."""
    return {k: {"mu": v[0], "sd": v[1]} for k, v in C.LATENT_SPECS.items()}


def anchor_priors():
    """sim.config.ANCHOR_PRIORS (튜플→배열은 JSON 직렬화가 처리)."""
    return C.ANCHOR_PRIORS


def _schema_fields(src):
    """wf_vs_v23.js SCHEMA required 필드 목록(권위 있는 구조)."""
    m = re.search(r"required:\s*\[([^\]]+)\]", src, re.S)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1))


def v23_questions():
    """wf_vs_v23.js 프롬프트에서 문항·보기 파싱(best-effort — 형식 고정 전제)."""
    src = open(WF_V23, encoding="utf-8").read()
    fields = _schema_fields(src)
    items = []
    # 패턴 A: `X_dist [opt / opt / ...] — 라벨`
    for m in re.finditer(r"^([A-Za-z0-9]+)_dist \[([^\]]+)\] — (.+)$", src, re.M):
        field, opts, label = m.group(1), m.group(2), m.group(3)
        options = [o.strip() for o in opts.split("/")]
        items.append({"field": f"{field}_dist", "type": "categorical",
                      "options": options, "label": label.strip()})
    # 패턴 B: `A2a_dist — (a) 라벨` (A2a~A2d, 각 3점 척도)
    for m in re.finditer(r"^(A2[abcd])_dist — (.+)$", src, re.M):
        items.append({"field": f"{m.group(1)}_dist", "type": "scale3",
                      "scale": ["아니다", "조금 그렇다", "매우 그렇다"], "label": m.group(2).strip()})
    # 패턴 C: D1 가격 사다리 `buy_NNNN (N,NNN원)` → 하나의 문항으로 묶음
    prices = [m.group(1) for m in re.finditer(r"buy_(\d+) \([\d,]+원\)", src)]
    if prices:
        items.append({"field": "D1(buy_*)", "type": "price_ladder",
                      "prices": [int(p) for p in prices], "accept_options": ["산다", "안 산다"],
                      "label": "가격 수용(Gabor-Granger, 각 가격 산다/안 산다)"})
    # 컨셉 카드
    cm = re.search(r"\[컨셉\]\s*(.+)", src)
    concept = cm.group(1).strip() if cm else None
    # SCHEMA 상 필드 순서로 정렬(권위)
    order = {f: i for i, f in enumerate(fields)}
    items.sort(key=lambda it: order.get(it["field"], 999))
    # 파싱 안 된 필드 표기 (buy_* 는 D1 price_ladder 문항이 커버)
    parsed = {it["field"] for it in items}
    has_ladder = any(it["type"] == "price_ladder" for it in items)
    missing = [f for f in fields
               if f not in parsed and f != "pid" and not (has_ladder and f.startswith("buy_"))]
    return {"version": "v2.3", "source": "wf_vs_v23.js",
            "schema_required": fields, "items": items,
            "concept_card": concept,
            "unparsed_fields": missing,
            "note": "보기 라벨은 프롬프트 정적 파싱(형식 고정 전제). schema_required가 권위 구조."}


def design():
    return {"questions": v23_questions(),
            "latent_specs": latent_specs(),
            "anchor_priors": anchor_priors()}
