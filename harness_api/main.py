# -*- coding: utf-8 -*-
"""Research Harness UI 백엔드 — FastAPI 앱(SPEC §1).

읽기 레이어(P2-1): runs/ 스캔 + 설계 뷰어 데이터.
모든 상태는 runs/ 파일. DB 없음. 엔진 코드는 읽기만.
실행:  uvicorn harness_api.main:app --port 8781   (repo 루트에서)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import REPO_ROOT
from . import store, design as design_mod, analysis
import harness_paths as H

app = FastAPI(title="Gate C Research Harness", version="0.1 (P2-1)")

# 로컬 단일 유저 — 개발 중 프론트(Vite dev server)에서의 접근 허용.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "repo": REPO_ROOT, "runs_dir": H.RUNS_DIR,
            "sp": H.SP, "journal_base": H.JOURNAL_BASE}


@app.get("/api/runs")
def runs():
    return {"runs": store.list_runs()}


@app.get("/api/pools")
def pools():
    return {"pools": store.list_pools()}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    r = store.get_run(run_id)
    if r is None:
        raise HTTPException(404, f"run 없음: {run_id}")
    return r


@app.get("/api/pools/{pool_id}")
def pool_detail(pool_id: str):
    p = store.get_pool(pool_id)
    if p is None:
        raise HTTPException(404, f"pool 없음: {pool_id}")
    return p


@app.get("/api/design")
def design():
    return design_mod.design()


@app.get("/api/runs/{run_id}/diagnose")
def diagnose(run_id: str):
    """붕괴/동질성 진단(v2.3 저널 → v23_verify.py JSON). SPEC §5.2 진단 패널."""
    if store.get_run(run_id) is None:
        raise HTTPException(404, f"run 없음: {run_id}")
    fmt = analysis.journal_format(run_id)
    if fmt != "v2.3":
        return {"run_id": run_id, "format": fmt, "diagnosable": False,
                "note": "v2.3(A2a_dist) 저널만 진단 대상. 레거시 wf_vs_all은 vs_verify(별도·텍스트)."}
    try:
        data = analysis.run_json_script("v23_verify.py", run_id)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    data["format"] = "v2.3"
    data["diagnosable"] = True
    return data
