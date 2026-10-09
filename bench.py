"""Measure real local inference speed for the README. Run: python bench.py"""
from __future__ import annotations

import time

import requests

URL = "http://localhost:1234/v1/chat/completions"
PAYLOAD = {
    "model": "qwen2.5-3b-instruct",
    "temperature": 0.0,
    "max_tokens": 160,
    "messages": [
        {"role": "system", "content": "Reply ONLY with JSON."},
        {"role": "user", "content":
            "Classify as scam or safe. SMS: GCash account suspended, verify at "
            "http://gcash-ph.xyz and send OTP. JSON: verdict, reasons, explanation"},
    ],
}


def once() -> tuple[float, int]:
    t0 = time.perf_counter()
    r = requests.post(URL, json=PAYLOAD, timeout=60)
    dt = time.perf_counter() - t0
    r.raise_for_status()
    usage = r.json().get("usage", {})
    return dt, int(usage.get("completion_tokens", 0))


def main() -> None:
    results = []
    for i in range(4):
        dt, toks = once()
        tps = toks / dt if dt else 0
        results.append((dt, toks, tps))
        print(f"run {i+1}: {dt:.2f}s, {toks} completion tokens, {tps:.1f} tok/s")

    # first run includes prompt processing warmup; report both
    warm = results[1:]
    avg_tps = sum(r[2] for r in warm) / len(warm)
    avg_dt = sum(r[0] for r in warm) / len(warm)
    print(f"\nWarm average: {avg_dt:.2f}s per scan, {avg_tps:.1f} tokens/sec")
    print(f"Cold first scan: {results[0][0]:.2f}s")
    print(f"\nREADME line: Qwen2.5-3B Q4_K_M on AMD Radeon 780M (Vulkan): "
          f"{avg_tps:.1f} tok/s, ~{avg_dt:.1f}s per verdict, fully offline")


if __name__ == "__main__":
    main()
