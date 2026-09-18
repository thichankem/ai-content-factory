"""Live check: can an agent score, fix and verify YouTube/TikTok SEO over HTTP?

Runs against a real server on ``sys.argv[1]`` and walks exactly the path an
external agent takes: discover the tools, score a pack, optimise it, then
*re-score the optimiser's own output* to prove the promised gain is real.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = f"http://127.0.0.1:{sys.argv[1] if len(sys.argv) > 1 else 8150}"
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{f' - {detail}' if detail else ''}")


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def call(tool: str, args: dict) -> tuple[int, dict]:
    return request("POST", "/tools/call", {"tool": tool, "args": args})


def get(path: str) -> tuple[int, dict]:
    return request("GET", path)


# --- 1. discovery ------------------------------------------------------------

status, manifest = get("/tools")
names = {tool["name"] for tool in manifest.get("tools", [])}
seo_tools = {name for name in names if name.startswith("seo_")}
check(
    "manifest exposes the seo category",
    status == 200 and "seo" in manifest.get("categories", []),
    f"{len(names)} tools total",
)
check("all 8 seo tools are discoverable", len(seo_tools) == 8, str(sorted(seo_tools)))
schema = next(
    (tool for tool in manifest["tools"] if tool["name"] == "seo_score"), None
)
required = schema["input_schema"].get("required", []) if schema else []
check("seo_score publishes a real JSON schema", required == ["pack"], str(required))

# --- 2. the rules themselves -------------------------------------------------

status, rules = get("/seo/rules")
platforms = {row["platform"] for row in rules} if isinstance(rules, list) else set()
check(
    "rules cover youtube, shorts and tiktok",
    status == 200 and {"youtube", "youtube_shorts", "tiktok"} <= platforms,
    f"{len(rules) if isinstance(rules, list) else 0} profiles",
)
weights = sum(rules[0]["dimensions"].values()) if isinstance(rules, list) else 0
check("youtube dimension weights sum to 1.0", abs(weights - 1.0) < 1e-9, f"{weights}")

# --- 3. score a pack ---------------------------------------------------------

PACK = {
    "title": "Tàu Titanic",
    "description": "Chuyện con tàu.",
    "keywords": ["tàu titanic"],
    "aspect_ratio": "16:9",
    "duration_seconds": 240.0,
    "has_captions": True,
    "hook": "Con tàu này được cho là không thể chìm.",
}
status, score = call("seo_score", {"platform": "youtube", "pack": PACK})
check(
    "seo_score returns a 0-100 score with dimensions",
    status == 200 and 0 <= score["score"] <= 100 and score["dimensions"],
    f"{score.get('score')}/100 grade {score.get('grade')}",
)
check(
    "score explains itself (quick wins + notes)",
    bool(score.get("quick_wins")) and bool(score.get("notes")),
    f"{len(score.get('quick_wins', []))} quick wins",
)
status, again = call("seo_score", {"platform": "youtube", "pack": PACK})
check(
    "scoring is deterministic across calls",
    again.get("score") == score.get("score"),
    f"{score.get('score')} == {again.get('score')}",
)

status, both = call("seo_score", {"platform": "all", "pack": PACK})
check(
    "platform=all scores every profile",
    status == 200 and {"youtube", "tiktok"} <= set(both),
    str(list(both)[:2]),
)

# --- 4. optimise, then verify the promise with an independent score ----------

status, plan = call("seo_optimize", {"platform": "youtube", "pack": PACK})
check(
    "seo_optimize reports before/after and changes",
    status == 200 and plan["after"]["score"] >= plan["before"]["score"],
    f"{plan['before']['score']} -> {plan['after']['score']} (gain {plan['gain']})",
)
optimized = dict(plan["pack"])
optimized.update(  # keep the context the optimiser cannot rewrite
    {
        "keywords": PACK["keywords"],
        "aspect_ratio": PACK["aspect_ratio"],
        "duration_seconds": PACK["duration_seconds"],
        "has_captions": PACK["has_captions"],
        "hook": PACK["hook"],
    }
)
status, rescored = call("seo_score", {"platform": "youtube", "pack": optimized})
check(
    "the optimiser's output scores what it promised",
    status == 200 and rescored["score"] == plan["after"]["score"],
    f"re-scored {rescored.get('score')} vs promised {plan['after']['score']}",
)

# --- 5. score a real project -------------------------------------------------

created = request(
    "POST", "/projects", {"name": "SEO live", "topic": "Thảm hoạ Titanic"}
)
project_id = created[1].get("id", "")
call(
    "update_script",
    {
        "project_id": project_id,
        "script": "[Hook]\nCon tàu không thể chìm.\n\n[Outro]\nKết.",
        "source_rights_confirmed": True,
    },
)
call(
    "approve_stage",
    {"project_id": project_id, "stage": "script", "verdict": "approved"},
)
call("build_video_project", {"project_id": project_id})
status, report = call(
    "seo_score_project", {"project_id": project_id, "platform": "all"}
)
check(
    "seo_score_project reads the stored script and timeline",
    status == 200
    and report["pack_used"]["hook"].startswith("Con tàu")
    and report["pack_used"]["duration_seconds"] is not None,
    f"hook from script, {report.get('pack_used', {}).get('duration_seconds')}s",
)
check(
    "project report covers both platforms",
    {"youtube", "tiktok"} <= set(report.get("platforms", {})),
    str(sorted(report.get("platforms", {}))),
)

# --- 6. A/B: a real winner, and a tie that is called a tie -------------------

status, sizing = call(
    "seo_ab_plan", {"metric": "ctr", "baseline_rate": 0.04, "daily_traffic": 5000}
)
check(
    "seo_ab_plan sizes the test in impressions and days",
    status == 200 and sizing["per_arm"] > 0 and sizing["days"] > 0,
    f"{sizing['per_arm']}/arm, {sizing['days']} days",
)
status, verdict = call(
    "seo_ab_evaluate",
    {
        "metric": "ctr",
        "arms": [
            {"name": "control", "impressions": 40000, "clicks": 1600},
            {"name": "variant_b", "impressions": 40000, "clicks": 2200},
        ],
    },
)
check(
    "a real lift is called a winner with a p-value",
    status == 200 and verdict["winner"] == "variant_b" and verdict["p_value"] < 0.05,
    f"p={verdict.get('p_value')} lift {verdict.get('lift_relative')}",
)
status, noise = call(
    "seo_ab_evaluate",
    {
        "metric": "ctr",
        "arms": [
            {"name": "control", "impressions": 100, "clicks": 4},
            {"name": "variant_b", "impressions": 100, "clicks": 5},
        ],
    },
)
check(
    "a coin-flip is not declared a winner",
    status == 200 and noise["winner"] != "variant_b",
    str(noise.get("verdict"))[:70],
)

# --- 7. keywords, calibration, and honest errors -----------------------------

status, ranked = call(
    "seo_keywords",
    {
        "keywords": ["tàu titanic", "thảm hoạ hàng hải"],
        "competitors": [
            {"title": "Tàu Titanic chìm", "views": 120000, "subscribers": 5000},
            {"title": "Bí ẩn Titanic", "views": 80000, "subscribers": 900},
        ],
    },
)
check(
    "seo_keywords ranks demand vs competition",
    status == 200 and len(ranked.get("rows", [])) == 2,
    str([row["keyword"] for row in ranked.get("rows", [])]),
)
status, calibration = call(
    "seo_calibrate",
    {
        "platform": "youtube",
        "observations": [
            {"signals": {"hook_strength": 40, "packaging": 30}, "outcome": 900},
            {"signals": {"hook_strength": 70, "packaging": 60}, "outcome": 2600},
            {"signals": {"hook_strength": 90, "packaging": 85}, "outcome": 5400},
        ],
    },
)
check(
    "seo_calibrate correlates signals with real outcomes",
    status == 200 and calibration.get("correlations"),
    f"{len(calibration.get('correlations', []))} signals measured",
)

status, body = call("seo_score", {"platform": "myspace", "pack": PACK})
check(
    "unknown platform is rejected with a readable 422",
    status == 422 and "myspace" in str(body.get("detail")),
    str(body.get("detail"))[:60],
)
status, body = call("seo_score", {"platform": "youtube"})
check(
    "missing required argument is caught at dispatch",
    status == 422 and "pack" in str(body.get("detail")),
    str(body.get("detail"))[:60],
)
status, body = call("seo_score_project", {"project_id": "missing-project"})
check("unknown project maps to 404", status == 404, str(body.get("detail"))[:60])
status, body = call("seo_ab_evaluate", {"arms": [{"name": "solo"}]})
check(
    "one arm cannot be evaluated as a test",
    status == 422 and "two" in str(body.get("detail")),
    str(body.get("detail"))[:60],
)

failed = [name for name, ok, _ in CHECKS if not ok]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} live SEO checks passed")
if failed:
    print("failed:", failed)
sys.exit(1 if failed else 0)
