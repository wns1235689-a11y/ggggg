# -*- coding: utf-8 -*-
"""경로 일원화(SPEC P0-1) — 현행 계보 전용.

SP(스크래치패드)·저널 BASE·runs/ 경로를 환경변수로 오버라이드한다.
환경변수 미지정 시 **기존 세션 경로를 그대로 기본값**으로 사용하므로,
이 모듈로 치환한 스크립트의 무-환경변수 동작은 종전과 바이트 동일하다.

환경변수:
  HARNESS_SP            — 스크래치패드 디렉토리 (풀 파일·중간 JSON)
  HARNESS_JOURNAL_BASE  — 워크플로 저널 루트 (<BASE>/<run_id>/journal.jsonl)
  HARNESS_RUNS          — 런 영속 저장소 (기본: 이 repo 루트의 runs/)

주의: 레거시 파일(LEGACY.md 목록)은 이 모듈을 참조하지 않는다(무변경).
"""
import os

# 기존 세션 경로(기본값) — INVENTORY §4a에서 확인된 하드코딩 값과 동일.
_DEFAULT_SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
_DEFAULT_JOURNAL_BASE = "/root/.claude/projects/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/subagents/workflows"
_REPO = os.path.dirname(os.path.abspath(__file__))

SP = os.environ.get("HARNESS_SP", _DEFAULT_SP)
JOURNAL_BASE = os.environ.get("HARNESS_JOURNAL_BASE", _DEFAULT_JOURNAL_BASE)
RUNS_DIR = os.environ.get("HARNESS_RUNS", os.path.join(_REPO, "runs"))


def sp_path(name: str) -> str:
    """스크래치패드 내 파일 경로."""
    return os.path.join(SP, name)


def journal_path(run_id: str) -> str:
    """워크플로 런ID의 journal.jsonl 경로."""
    return os.path.join(JOURNAL_BASE, run_id, "journal.jsonl")


def run_dir(run_or_pool_id: str, create: bool = False) -> str:
    """runs/<id>/ 디렉토리 경로. create=True면 생성."""
    d = os.path.join(RUNS_DIR, run_or_pool_id)
    if create:
        os.makedirs(d, exist_ok=True)
    return d
