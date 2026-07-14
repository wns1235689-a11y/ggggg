#!/usr/bin/env python3
"""
정밀설문 응답(풀텍스트) → 표준라벨 매핑 → ingest_live → VS 패치(B1/C1/C2) → §3 집계.
RUN_SEED로 전 파이프라인 시드 일관(풀 재현·B4·직진·VS표집 동일 시드).
"""
import json
import numpy as np

SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
cfg = json.load(open(f"{SP}/run_cfg.json"))
N, RUN_SEED = cfg["N"], cfg["RUN_SEED"]

import sim.config as C
C.GLOBAL_SEED = RUN_SEED                      # 신규 표본 시드로 전 파이프라인 재현
from sim import ingest, respondent, aggregate

# ── 풀텍스트 → 표준라벨 매핑(§3 규칙 호환) ──
A2_MAP = {
    "고수 등 향신료 향이 부담스러워서": "①향신료향 부담",
    "피시소스 등 낯선 소스·재료가 부담스러워서": "②낯선 소스·재료",
    "먹을 기회나 파는 곳이 마땅치 않아서": "③접근성 부족",
    "가격이 부담스러워서": "④가격 부담",
    "동남아 음식 자체를 즐기지 않아서": "⑤단순 비선호",
    "지금도 거리낌 없이 잘 먹는다": "⑥지금도 잘 먹음",
}
B2_MAP = {
    "5분 완조리(간편함)": "5분 완조리", "외식 대비 가성비": "외식 대비 가성비",
    "국산 새우·숙주 등 재료": "국산 새우·숙주 등 재료", "매실청의 새콤한 맛": "매실청의 새콤한 맛",
    "향신료(고수 등) 부담 없음": "향신료 부담 없음", "사고 싶은 이유 없음": "사고 싶은 이유 없음",
    "없음": "없음",
}
B3_MAP = {
    "맛이 상상이 안 된다": "맛 상상 안 됨", "'진짜 팟타이 맛'이 아닐 것 같다": "진짜 팟타이 아닐 것",
    "냉동식품 품질을 믿기 어렵다": "냉동품질 불신", "가격이 걱정된다": "가격 걱정",
    "양(1인분 300g)이 부족할 것 같다": "양(300g) 부족", "팟타이 자체에 관심이 없다": "팟타이 관심 없음",
    "망설여지는 점 없다": "망설임 없음",
}
C1_MAP = {
    "직접 만든다": "직접 만든다", "냉동/밀키트를 사 먹는다": "냉동/밀키트", "배달·외식": "배달·외식",
    "안 먹거나 참는다": "안 먹거나 참는다", "이런 맛을 안 찾는다": "이런 맛 안 찾음",
}
C2_MAP = {"꼭 산다": "꼭 산다", "상황 보고 가끔 산다": "가끔 산다", "아니오, 기존 방식 유지": "기존 방식 유지"}
E1_MAP = {"가": "가(T1·완성도)", "나": "나(T2·매실청)", "비슷": "비슷", "둘다": "둘 다 안 끌림"}


def to_canonical(a: dict) -> dict:
    return {
        "pid": a["pid"], "A1": a["A1"], "A2": A2_MAP[a["A2"]],
        "B1": int(a["B1"]), "B2_1": B2_MAP[a["B2_1"]], "B2_2": B2_MAP.get(a["B2_2"], "없음"),
        "B3": B3_MAP[a["B3"]], "B4": a["B4"],
        "C1": C1_MAP[a["C1"]], "C2": C2_MAP[a["C2"]],
        "D1_5900": a["D1_5900"], "D1_6900": a["D1_6900"],
        "D1_7500": a["D1_7500"], "D1_8500": a["D1_8500"],
        "E1": E1_MAP[a["E1"]], "E2": a.get("E2", ""),
        "B1_why": "", "B2_why": "",
    }


def vs_sample(dist, options, pid, itemid, tilt=None):
    w = np.array([max(float(x), 0.0) for x in dist])
    if tilt is not None:
        w = w * np.asarray(tilt, float)          # 성향 결합(예: B1로 C2 기울임)
    if w.sum() <= 0:
        w = np.ones(len(options))
    rng = np.random.default_rng([C.GLOBAL_SEED, pid, itemid])
    return options[int(rng.choice(len(options), p=w / w.sum()))]


D1P = [5900, 6900, 7500, 8500]


def d1_from_curve(dist, pid):
    """VS 수용인원(각 가격 0~10) → 단조 수용확률 → WTP 임계 분포에서 1개 표집.
    임계 이하 가격만 '산다'(단조). §3-15 현실성 위해 소량 상승꺾임(비단조) 주입."""
    p = [min(max(float(x) / 10.0, 0.0), 1.0) for x in dist]
    for i in range(1, 4):                     # 가격↑ → 수용 감소(단조) 강제
        p[i] = min(p[i], p[i - 1])
    # 임계구간 확률: 최저가부터 k개 가격을 '산다'(k=0..4)
    bins = [1 - p[0], p[0] - p[1], p[1] - p[2], p[2] - p[3], p[3]]
    bins = [max(b, 0.0) for b in bins]
    s = sum(bins) or 1.0
    bins = [b / s for b in bins]
    rng = np.random.default_rng([C.GLOBAL_SEED, pid, 51])
    k = int(rng.choice(5, p=bins))
    seq = ["산다" if i < k else "안 산다" for i in range(4)]
    # §3-15 비단조 소량 주입(임계 근처 상승꺾임) — 실측에도 존재하는 응답오류
    if 0 < k < 4 and rng.random() < C.ANCHOR_PRIORS["D1_nonmonotone_rate"][1]:
        seq[k - 1], seq[k] = "안 산다", "산다"
    return {D1P[i]: seq[i] for i in range(4)}


def c2_tilt(b1):
    """C2[꼭,가끔,기존]를 첫인상 B1로 기울여 정합화(VS 분산 유지, 순서 존중)."""
    t = (b1 - 3) / 2.0                            # B1 1..5 → t -1..+1
    return [max(1 + 0.8 * t, 0.05),               # 꼭 산다: 높은 B1일수록 ↑
            1.0,                                   # 가끔 산다: 중립
            max(1 - 0.8 * t, 0.05)]               # 기존 유지: 낮은 B1일수록 ↑


def main():
    raw = json.load(open(f"{SP}/survey_raw.json"))       # 워크플로 responses
    dists = {d["pid"]: d for d in json.load(open(f"{SP}/dist_raw.json"))}
    canon = [to_canonical(a) for a in raw]

    rows = ingest.ingest_live(canon, n=N)                # 표준 스키마 + 노이즈(B4/직진/비단조)

    # VS 분포로 B1/C1/C2 표집(모드붕괴 방지) — 표준라벨
    C1_OPT = ["직접 만든다", "냉동/밀키트", "배달·외식", "안 먹거나 참는다", "이런 맛 안 찾음"]
    C2_OPT = ["꼭 산다", "가끔 산다", "기존 방식 유지"]
    for r in rows:
        d = dists.get(r["respondent_id"])
        if not d:
            continue
        b1 = int(vs_sample(d["B1_dist"], [1, 2, 3, 4, 5], r["respondent_id"], 1))
        r["B1"] = b1
        r["C1"] = vs_sample(d["C1_dist"], C1_OPT, r["respondent_id"], 2)
        c2 = vs_sample(d["C2_dist"], C2_OPT, r["respondent_id"], 3, tilt=c2_tilt(b1))
        # 최극단 정합만 클램프: B1=1(최악 첫인상) & 꼭 산다(최강 의향)은 비현실 → 가끔 산다.
        # (B1=2 등 완화 모순은 실측 부주의로 보존)
        if b1 == 1 and c2 == "꼭 산다":
            c2 = "가끔 산다"
        r["C2"] = c2

    # Q017 구조적 불일치(워크북): 첫인상 좋아도(B1>=4) 소수는 전환 보수화 — 잔존 노이즈로 소량만
    for r in rows:
        rngi = np.random.default_rng([C.GLOBAL_SEED, r["respondent_id"], 17])
        if rngi.random() < C.STRUCTURAL_INCONSISTENCY_RATE and r["B1"] >= 4:
            r["C2"] = {"꼭 산다": "가끔 산다", "가끔 산다": "기존 방식 유지"}.get(r["C2"], r["C2"])
            r["_flag_structural_inconsistency"] = True

    # D1 가격수용 이질화(모드붕괴 수정): VS 수용곡선 → 응답자별 WTP 임계 표집(Gabor-Granger)
    import os
    d1path = f"{SP}/d1_raw.json"
    if os.path.exists(d1path):
        d1d = {d["pid"]: d for d in json.load(open(d1path))}
        for r in rows:
            d = d1d.get(r["respondent_id"])
            if not d:
                continue
            seq = d1_from_curve([d["buy_5900"], d["buy_6900"], d["buy_7500"], d["buy_8500"]],
                                r["respondent_id"])
            # 극단 정합 가드(진술의향↔현시 WTP): 강한 구매의향인데 최저가에도 안 삼 → 최저가 수용,
            # 약한 의향인데 최고가까지 삼 → 최고가 제외. (중간대 가격저항은 자연스러워 보존)
            strong = seq.get(5900) == "안 산다" and (
                r["C2"] == "꼭 산다" or (r["B1"] >= 4 and r["C2"] == "가끔 산다"))
            if strong:
                seq[5900] = "산다"
            weak = all(seq[pr] == "산다" for pr in D1P) and r["B1"] <= 2 and r["C2"] == "기존 방식 유지"
            if weak:
                seq[8500] = "안 산다"
            for i, pr in enumerate(D1P):
                r[f"D1_{pr}"] = seq[pr]
            acc = [seq[pr] == "산다" for pr in D1P]
            r["_flag_d1_nonmonotone"] = any(acc[i] < acc[i + 1] for i in range(3))

    json.dump(rows, open(f"{SP}/rows_final.json", "w"), ensure_ascii=False)

    agg = aggregate.aggregate(rows)
    json.dump(agg, open(f"{SP}/agg_final.json", "w"), ensure_ascii=False)

    # 검증 요약
    A = agg["A_설계리스크_운영점검"]
    B = agg["B_방향성_사전분포"]
    print(f"N={N} RUN_SEED={RUN_SEED}")
    print("유효표본:", A["N_유효(§3-2 B4제외후)"]["value"], "/ 1차대상:", A["N_1차대상(§3-1)"]["value"],
          "/ 대학생:", A["N_대학생(§3-3 별도)"]["value"])
    print("B1:", B["B1_첫인상"]["value"])
    print("C1:", B["C1_대안구조"]["value"])
    print("C2:", B["C2_전환의향"]["value"]["분포"])
    print("E1:", B["E1_헤드라인"]["value"])
    print("A2 유병률:", B["A2_향기피유병률(§3-12)"]["value"])
    print("B2 계열:", B["B2_계열방향(§3-11)"]["value"]["A계열_1순위"], "vs C계열", B["B2_계열방향(§3-11)"]["value"]["C계열_1순위"])
    print("D1:", B["D1_수용곡선"]["value"])
    # E2 응답 현황
    e2n = sum(1 for r in rows if r["E2"].strip())
    print(f"E2 원응답 존재: {e2n}/{len(rows)}")


if __name__ == "__main__":
    main()
