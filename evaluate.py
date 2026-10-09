"""Honest evaluation over test_set.csv. Never edits the test set.

Usage:  python evaluate.py
Prints per-type accuracy, false positives, false negatives, and latency.
"""
from __future__ import annotations

import csv
import sys
from time import perf_counter

import rules
import scoring
from llm import classify, server_up

CSV_FILE = "test_set.csv"


def load_rows() -> list[dict]:
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r.get("label") in ("phishing", "scam"):
            r["label"] = "scam"
        else:
            r["label"] = "legit"
    return rows


def run_one(row: dict, llm_on: bool = True) -> dict:
    kind = row.get("type") or "sms"
    text = row.get("text") or ""
    meta = None
    if kind == "email":
        meta = {
            "sender": row.get("sender") or "",
            "reply_to": row.get("reply_to") or "",
            "subject": row.get("subject") or "",
            "attachments": [],
        }
    t0 = perf_counter()
    rule_result = rules.check(text, kind, meta)
    llm_result = classify(text, kind, meta) if llm_on else None
    result = scoring.combine(rule_result, llm_result)
    latency = perf_counter() - t0
    return {"level": result["level"], "score": result["score"],
            "llm_used": result["llm_used"], "latency": latency,
            "flags": [f["name"] for f in result["flags"]]}


def summarize(rows: list[dict], results: list[dict], name: str) -> dict:
    n = len(rows)
    scams = [(r, p) for r, p in zip(rows, results) if r["label"] == "scam"]
    legits = [(r, p) for r, p in zip(rows, results) if r["label"] == "legit"]

    caught = [p for _, p in scams if p["level"] in ("red", "yellow")]
    red_hits = [p for _, p in scams if p["level"] == "red"]
    fp = [p for _, p in legits if p["level"] in ("red", "yellow")]
    hard_fp = [p for _, p in legits if p["level"] == "red"]

    # strict: red = predicted scam, green = predicted safe, yellow = abstain
    decided = [(r, p) for r, p in zip(rows, results) if p["level"] in ("red", "green")]
    strict_ok = sum(1 for r, p in decided
                    if (r["label"] == "scam") == (p["level"] == "red"))

    lat = [p["latency"] for p in results]
    stats = {
        "name": name, "n": n,
        "n_scams": len(scams), "n_legit": len(legits),
        "detected": len(caught), "red_hits": len(red_hits),
        "fp": len(fp), "hard_fp": len(hard_fp),
        "strict_acc": (strict_ok / len(decided) * 100) if decided else 0.0,
        "abstain": n - len(decided),
        "avg_lat": sum(lat) / len(lat) if lat else 0.0,
        "max_lat": max(lat) if lat else 0.0,
        "llm_rate": sum(1 for p in results if p["llm_used"]) / n * 100 if n else 0,
    }
    return stats


def main() -> int:
    rows = load_rows()
    if not rows:
        print("test_set.csv is empty")
        return 1

    up = server_up()
    print(f"LM Studio server: {'UP' if up else 'DOWN (rules-only run)'}")
    print(f"Running {len(rows)} messages through the full pipeline...\n")

    results: list[dict] = []
    for i, row in enumerate(rows, 1):
        r = run_one(row, llm_on=up)
        results.append(r)
        mark = "OK " if (row["label"] == "scam") == (r["level"] == "red") else "MISS"
        if row["label"] == "legit" and r["level"] != "green":
            mark = "FP  "
        print(f"[{i:2d}/{len(rows)}] {mark} {row['type']:5s} {row['label']:6s} "
              f"-> {r['level']:6s} ({r['score']:3d}) {r['latency']:.2f}s")

    print("\n" + "=" * 70)
    sms_rows = [r for r in rows if r["type"] == "sms"]
    sms_res = [results[i] for i, r in enumerate(rows) if r["type"] == "sms"]
    em_rows = [r for r in rows if r["type"] == "email"]
    em_res = [results[i] for i, r in enumerate(rows) if r["type"] == "email"]

    stats = [summarize(sms_rows, sms_res, "SMS"),
             summarize(em_rows, em_res, "Email"),
             summarize(rows, results, "TOTAL")]

    print(f"{'':8s} {'n':>3s} {'scam':>5s} {'legit':>6s} {'caught':>7s} "
          f"{'red':>5s} {'FP':>4s} {'hardFP':>7s} {'strict':>7s} {'avg s':>6s}")
    for s in stats:
        if s["n"] == 0:
            continue
        print(f"{s['name']:8s} {s['n']:3d} {s['n_scams']:5d} {s['n_legit']:6d} "
              f"{s['detected']:3d}/{s['n_scams']:<3d} {s['red_hits']:5d} "
              f"{s['fp']:4d} {s['hard_fp']:7d} {s['strict_acc']:6.1f}% "
              f"{s['avg_lat']:6.2f}")

    total = stats[2]
    print(f"\nDetection rate (scam not green): "
          f"{total['detected']}/{total['n_scams']}")
    print(f"False alarm rate (legit not green): {total['fp']}/{total['n_legit']}")
    print(f"Strict accuracy (red=scam, green=legit, yellow=abstain): "
          f"{total['strict_acc']:.1f}%  (abstained: {total['abstain']})")
    print(f"Latency avg {total['avg_lat']:.2f}s, max {total['max_lat']:.2f}s")
    print(f"LLM used on {total['llm_rate']:.0f}% of messages "
          f"({'server up' if up else 'server DOWN'})")

    misses = [(r, p) for r, p in zip(rows, results)
              if not ((r["label"] == "scam") == (p["level"] == "red")
                      or (r["label"] == "legit" and p["level"] == "green"))]
    if misses:
        print("\nNon-green/misses (honest list):")
        for r, p in misses:
            print(f"  [{r['type']}] label={r['label']:6s} got={p['level']:6s} "
                  f"score={p['score']:3d} flags={','.join(p['flags']) or '-'} "
                  f"| {r['text'][:70]}")

    # machine-readable line for README
    print(f"\nREADME line: detection {total['detected']}/{total['n_scams']}, "
          f"false alarms {total['fp']}/{total['n_legit']}, "
          f"strict {total['strict_acc']:.0f}%, "
          f"avg latency {total['avg_lat']:.2f}s, n={total['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
