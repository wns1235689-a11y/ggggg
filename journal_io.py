# -*- coding: utf-8 -*-
"""설문 플러그인 공용 저널 로더 (판정단 F8).

persist_run은 20MB 초과 저널을 journal.jsonl.gz로 남기는데, 설문 verify/judge가
평문만 열면 FileNotFoundError → API 500이 된다. 하니스 계층(store/registry)과 동일하게
gz 폴백 + 행 단위 손상 내성(스킵 카운트 보고)을 제공한다.
"""
import gzip
import json
import os


def iter_results(base, run_id, marker):
    """(result_dict 제너레이터, skipped 리스트에 손상행 수 기록)."""
    skipped = [0]

    def _gen():
        for name in ("journal.jsonl", "journal.jsonl.gz"):
            p = os.path.join(base, run_id, name)
            if not os.path.exists(p):
                continue
            opener = (lambda: gzip.open(p, "rt", encoding="utf-8")) if name.endswith(".gz") \
                else (lambda: open(p, encoding="utf-8"))
            with opener() as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        skipped[0] += 1
                        continue
                    r = o.get("result")
                    if o.get("type") == "result" and isinstance(r, dict) and marker in r:
                        yield r
            return
    return _gen(), skipped


def journal_exists(base, run_id):
    return any(os.path.exists(os.path.join(base, run_id, n))
               for n in ("journal.jsonl", "journal.jsonl.gz"))


def load_rows(base, run_id, marker):
    """{pid: result} + {"skipped": 손상행 수, "missing": 저널 파일 부재 여부}.
    missing=True는 '진행 중'이 아니라 run_id 오타·경로 문제일 수 있음(공격수 F8 보강)."""
    gen, skipped = iter_results(base, run_id, marker)
    rows = {r["pid"]: r for r in gen}
    return rows, {"skipped": skipped[0], "missing": not journal_exists(base, run_id)}
