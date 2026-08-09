# -*- coding: utf-8 -*-
"""설문 매니페스트 레지스트리 — 하니스의 설문 하드코딩 제거(라우팅 전용).

배경: 하니스(러너·잡·저장소·플러그인 계약)는 설문 무관이지만, 스크립트 화이트리스트·
저널 포맷 스니핑·판정 스크립트 매핑이 게이트C v2.3에 하드코딩돼 있었다(6개 지점).
이 모듈은 그 지점들을 surveys/<id>/manifest.json 선언으로 치환한다.

매니페스트 계약(surveys/<survey_id>/manifest.json):
  {
    "survey_id":      str  — 디렉토리명과 일치
    "label":          str  — UI 표시명
    "journal_marker": str  — 저널 result 행에서 이 설문을 식별하는 필드명
    "builds":         {kind: 스크립트 경로}  — 풀 생성(kind는 전역 유일)
    "wf_scripts":     [경로]                — 러너 허용 워크플로
    "verify":         경로 | null           — 진단 플러그인(JSON stdout)
    "judge":          경로 | {"single":…,"multipool":…} | null — 판정 플러그인
    "report":         경로 | "legacy" | null — 리포트 플러그인({markdown} JSON) /
                                               "legacy"=harness_api.report 조립 경로
    "curve":          "legacy_d1" | null    — 가격사다리 곡선(게이트C 전용 내장) 유무
  }
모든 경로는 repo 루트 기준 상대경로. 플러그인 계약은 기존과 동일:
`python3 <script> <run_id>` + harness_paths 환경변수 → JSON stdout.

엔진 무수정: 게이트C 계보 파일은 건드리지 않고 manifest(surveys/gatec_v23/)가
기존 루트 스크립트를 가리킨다. 레거시 v1.x(wf_vs_all) 저널은 종전대로 비진단 대상.
"""
import json
import os

REPO = os.path.dirname(os.path.abspath(__file__))
SURVEYS_DIR = os.path.join(REPO, "surveys")


def _load_manifest(path):
    try:
        m = json.load(open(path, encoding="utf-8"))
        return m if isinstance(m, dict) and m.get("survey_id") else None
    except Exception:
        return None


def manifests():
    """{survey_id: manifest} — surveys/*/manifest.json 스캔(호출 시점 재스캔·캐시 없음)."""
    out = {}
    if not os.path.isdir(SURVEYS_DIR):
        return out
    for d in sorted(os.listdir(SURVEYS_DIR)):
        p = os.path.join(SURVEYS_DIR, d, "manifest.json")
        if os.path.isfile(p):
            m = _load_manifest(p)
            if m:
                out[m["survey_id"]] = m
    return out


def get(survey_id):
    return manifests().get(survey_id)


def wf_scripts():
    """러너 허용 워크플로 경로 집합(전 설문 합집합)."""
    s = set()
    for m in manifests().values():
        s.update(m.get("wf_scripts") or [])
    return s


def build_map():
    """{kind: 빌드 스크립트 경로}. kind 충돌 시 먼저 로드된 쪽 유지(사전순)."""
    out = {}
    for m in manifests().values():
        for kind, path in (m.get("builds") or {}).items():
            out.setdefault(kind, path)
    return out


def survey_for_wf(script):
    for sid, m in manifests().items():
        if script in (m.get("wf_scripts") or []):
            return sid
    return None


def judge_script(survey_id, kind=None):
    """판정 스크립트 경로(kind='multipool'이면 다풀 스크립트 우선)."""
    m = get(survey_id)
    if not m:
        return None
    j = m.get("judge")
    if isinstance(j, dict):
        return j.get(kind or "single") or j.get("single")
    return j


def _first_result_row(run_dir):
    import gzip
    for name in ("journal.jsonl", "journal.jsonl.gz"):
        p = os.path.join(run_dir, name)
        if not os.path.exists(p):
            continue
        opener = (lambda: gzip.open(p, "rt", encoding="utf-8")) if name.endswith(".gz") \
            else (lambda: open(p, encoding="utf-8"))
        try:
            with opener() as f:
                for line in f:
                    o = json.loads(line)
                    if o.get("type") == "result" and isinstance(o.get("result"), dict):
                        return o["result"]
        except Exception:
            return None
    return None


def detect_run(run_dir):
    """런 디렉토리의 설문 판별 → (survey_id, manifest) | (None, None).

    우선순위: ① params.json의 params.survey_id(러너 기록)
             ② 저널 첫 result 행의 journal_marker 스니핑
    v1.x 레거시 저널(A2_dist/E1_dist만)은 어떤 매니페스트에도 안 걸려 (None, None).
    """
    mans = manifests()
    try:
        params = json.load(open(os.path.join(run_dir, "params.json"), encoding="utf-8"))
        sid = ((params.get("params") or {}).get("survey_id"))
        if sid and sid in mans:
            return sid, mans[sid]
    except Exception:
        pass
    row = _first_result_row(run_dir)
    if row:
        for sid, m in mans.items():
            mk = m.get("journal_marker")
            if mk and mk in row:
                return sid, m
    return None, None
