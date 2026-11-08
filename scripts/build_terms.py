#!/usr/bin/env python3
"""One-off helper: build data/terms.json from every data/days/*.json.

The page doesn't load this script. The daily routine keeps terms.json up to
date afterwards; run this again only if terms.json gets lost or out of sync.

Usage (from the repo root): python3 scripts/build_terms.py
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ["term", "bangla", "definition", "example", "formula", "tip"]


def pick(src):
    return {f: (src or {}).get(f, "") or "" for f in FIELDS}


def main():
    terms, seen = [], set()
    # newest first, so a term repeated later keeps its newest entry
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "days", "*.json")), reverse=True):
        with open(path, encoding="utf-8") as fh:
            day = json.load(fh)
        tm = day.get("term")
        if not tm or not tm.get("term"):
            continue
        key = tm["term"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        entry = {"date": day["date"], **pick(tm)}
        en_term = (day.get("en") or {}).get("term")
        if en_term:
            entry["en"] = pick(en_term)
        terms.append(entry)
    out = os.path.join(ROOT, "data", "terms.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"terms": terms}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"wrote {len(terms)} terms to {out}")


if __name__ == "__main__":
    main()
