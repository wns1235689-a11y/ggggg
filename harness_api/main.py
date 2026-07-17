# -*- coding: utf-8 -*-
"""Research Harness UI 백엔드 — FastAPI 앱(SPEC §1).

읽기 레이어(P2-1): runs/ 스캔 + 설계 뷰어 데이터.
모든 상태는 runs/ 파일. DB 없음. 엔진 코드는 읽기만.
실행:  uvicorn harness_api.main:app --port 8781   (repo 루트에서)
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import REPO_ROOT
from . import store, design as design_mod, analysis, actions, report as report_mod, curve as curve_mod
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


@app.get("/api/runs/{run_id}/judge")
def judge(run_id: str):
    """방향성 판정(v23_judge/v23_multi_judge JSON). SPEC §5.3 판정 대시보드."""
    r = store.get_run(run_id)
    if r is None:
        raise HTTPException(404, f"run 없음: {run_id}")
    fmt = analysis.journal_format(run_id)
    if fmt != "v2.3":
        return {"run_id": run_id, "format": fmt, "judgeable": False,
                "note": "v2.3(A2a_dist) 저널만 판정 대상."}
    script = "v23_multi_judge.py" if r.get("kind") == "multipool" else "v23_judge.py"
    try:
        data = analysis.run_json_script(script, run_id)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    data["format"] = "v2.3"
    data["kind"] = r.get("kind")
    data["judgeable"] = True
    return data


@app.get("/api/runs/{run_id}/curve")
def curve(run_id: str):
    """D1 가격-수용 곡선(서술적 read). SPEC §5.3 판정 대시보드의 수용곡선 차트.
    판정 아님 — buy_ 평균만. 절대 높이 신뢰X(실측 몫), 기울기(방향)만 참고."""
    if store.get_run(run_id) is None:
        raise HTTPException(404, f"run 없음: {run_id}")
    fmt = analysis.journal_format(run_id)
    if fmt != "v2.3":
        return {"run_id": run_id, "format": fmt, "available": False,
                "note": "v2.3(A2a_dist) 저널만 D1 곡선 대상."}
    data = curve_mod.d1_curve(run_id)
    data["format"] = "v2.3"
    data["available"] = not data.get("empty", False)
    return data


@app.get("/api/runs/{run_id}/report")
def report(run_id: str):
    """리포트 자동 생성(게이트C_시뮬결과_정리.md 포맷). SPEC §5.4.
    ⓪ 합성·비실측·인용불가 경고 헤더는 하드코딩·항상 포함(끌 수 없음)."""
    data = report_mod.report(run_id)
    if data is None:
        raise HTTPException(404, f"run 없음: {run_id}")
    return data


# ── 액션(SPEC §5.1 실행 콘솔) ──
class PoolReq(BaseModel):
    kind: str = "single"           # single | multipool | sweep
    seed: Optional[int] = None
    n: Optional[int] = None


class RunReq(BaseModel):
    script: str                    # wf_vs_v23.js | wf_v23_multi.js
    pool_id: str
    effort: str = "medium"
    dry_run: bool = False
    n_limit: Optional[int] = None
    confirm_large: bool = False


@app.post("/api/pools")
def create_pool(req: PoolReq):
    """풀 생성(동기) — build_* 실행 → runs/<pool_id>/."""
    try:
        return actions.gen_pool(req.kind, seed=req.seed, n=req.n)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@app.post("/api/runs")
def create_run(req: RunReq):
    """시뮬 실행 트리거(백그라운드 잡). 비용 가드는 runner.py가 강제.
    반환된 job_id를 /api/jobs/{job_id}로 폴링."""
    if store.get_pool(req.pool_id) is None and store.get_run(req.pool_id) is None:
        raise HTTPException(404, f"pool/run 없음: {req.pool_id}")
    try:
        return actions.start_run(req.script, req.pool_id, effort=req.effort,
                                 dry_run=req.dry_run, n_limit=req.n_limit,
                                 confirm_large=req.confirm_large)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/jobs")
def jobs():
    return {"jobs": actions.list_jobs()}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    j = actions.get_job(job_id)
    if j is None:
        raise HTTPException(404, f"job 없음: {job_id}")
    return j
