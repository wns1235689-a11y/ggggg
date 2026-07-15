# -*- coding: utf-8 -*-
"""3개 워크플로 journal.jsonl → survey_raw.json / dist_raw.json / d1_raw.json 추출."""
import json, sys
SP = "/tmp/claude-0/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/scratchpad"
BASE = "/root/.claude/projects/-home-user-ggggg/8fffd176-9027-5172-8858-c1238d2e4b2b/subagents/workflows"

def collect(runid, key_field):
    res = {}
    for line in open(f"{BASE}/{runid}/journal.jsonl", encoding="utf-8"):
        o = json.loads(line)
        if o.get("type") == "result" and isinstance(o.get("result"), dict) and key_field in o["result"]:
            res[o["result"]["pid"]] = o["result"]
    return [res[k] for k in sorted(res)]

survey = collect(sys.argv[1], "A1")
dist = collect(sys.argv[2], "B1_dist")
d1 = collect(sys.argv[3], "buy_5900")
json.dump(survey, open(f"{SP}/survey_raw.json", "w"), ensure_ascii=False)
json.dump(dist, open(f"{SP}/dist_raw.json", "w"), ensure_ascii=False)
json.dump(d1, open(f"{SP}/d1_raw.json", "w"), ensure_ascii=False)
print(f"survey={len(survey)}  dist={len(dist)}  d1={len(d1)}")
