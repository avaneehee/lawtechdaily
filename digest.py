#!/usr/bin/env python3
"""
lawtech-daily
=============
Fetches law-tech / reg-tech / AI-governance articles, scores them for
relevance, picks one, summarises it with an LLM, and writes today.json
for a phone widget to consume.

Runs daily via GitHub Actions. Stdlib only except for the LLM call.

    python digest.py            # normal run
    python digest.py --dry-run  # no LLM call, no file writes
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from config import (
    CANDIDATE_POOL,
    FEEDS,
    HTTP_TIMEOUT,
    KEYWORDS,
    MIN_SCORE,
    SEEN_MEMORY,
    TAXONOMY,
    USER_AGENT,
)

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

TODAY_FILE   = DATA / "today.json"
ARCHIVE_FILE = DATA / "archive.json"
SEEN_FILE    = DATA / "seen.json"


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch(url: str) -> str | None:
    """GET a URL, returning text or None on failure. Never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  ! fetch failed {url[:60]}... ({e})", file=sys.stderr)
        return None


def strip_html(s: str) -> str:
    """Crude but adequate tag stripper for RSS summaries."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_feed(xml_text: str) -> list[dict]:
    """
    Parse RSS 2.0 or Atom into a common shape.
    Returns [] rather than raising on malformed XML.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[dict] = []

    # --- RSS 2.0 ---
    channel = root.find("channel")
    if channel is not None:
        source = strip_html(getattr(channel.find("title"), "text", "") or "")
        for it in channel.findall("item"):
            items.append({
                "title":   strip_html(getattr(it.find("title"), "text", "") or ""),
                "link":    (getattr(it.find("link"), "text", "") or "").strip(),
                "summary": strip_html(getattr(it.find("description"), "text", "") or ""),
                "published": (getattr(it.find("pubDate"), "text", "") or "").strip(),
                "source":  source,
            })
        return items

    # --- Atom ---
    source = strip_html(getattr(root.find("atom:title", ns), "text", "") or "")
    for e in root.findall("atom:entry", ns):
        link_el = e.find("atom:link", ns)
        items.append({
            "title":   strip_html(getattr(e.find("atom:title", ns), "text", "") or ""),
            "link":    (link_el.get("href") if link_el is not None else "").strip(),
            "summary": strip_html(
                getattr(e.find("atom:summary", ns), "text", "")
                or getattr(e.find("atom:content", ns), "text", "")
                or ""
            ),
            "published": (getattr(e.find("atom:updated", ns), "text", "") or "").strip(),
            "source":  source,
        })
    return items


# ---------------------------------------------------------------------------
# Scoring & tagging
# ---------------------------------------------------------------------------

def score_text(text: str) -> int:
    """Weighted keyword score. Word-boundary matched to avoid false hits."""
    t = text.lower()
    total = 0
    for kw, weight in KEYWORDS.items():
        pattern = re.escape(kw.strip())
        if re.search(rf"\b{pattern}", t):
            total += weight
    return total


def tag_article(text: str) -> str:
    """Assign the taxonomy label with the most keyword hits."""
    t = text.lower()
    best, best_hits = "LEGAL TECH", 0
    for label, terms in TAXONOMY.items():
        hits = sum(1 for term in terms if term in t)
        if hits > best_hits:
            best, best_hits = label, hits
    return best


def uid_for(link: str) -> str:
    return hashlib.sha1(link.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# LLM summarisation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You brief a Computing & Law student in Singapore who is building a career "
    "in AI governance, legal operations and RegTech. Be concrete and factual. "
    "Never pad. Never use marketing language."
)

USER_TEMPLATE = """Article headline: {title}
Source: {source}
Snippet: {summary}

Return STRICT JSON, no markdown fence, with exactly these keys:
  "summary"    - 2 sentences, max 45 words, what actually happened
  "why"        - 1 sentence, max 25 words, why it matters for AI governance / legal ops
  "framework"  - the single most relevant framework or regime mentioned or implied
                 (e.g. "EU AI Act", "PDPA", "NIST AI RMF", "ISO 42001", "None")
"""


def summarise(article: dict) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    fallback = {
        "summary": (article["summary"] or article["title"])[:220],
        "why": "",
        "framework": "None",
    }

    if not key:
        return fallback

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"

    payload = {
        "contents": [{
            "parts": [{"text": USER_TEMPLATE.format(
                title=article["title"],
                source=article.get("source", "unknown"),
                summary=article["summary"][:1500],
            )}]
        }]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read())
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = re.sub(r"^(?:json)?|$", "", text, flags=re.M).strip()
        parsed = json.loads(text)
        return {
            "summary": parsed.get("summary", fallback["summary"]),
            "why": parsed.get("why", ""),
            "framework": parsed.get("framework", "None"),
        }

    except Exception as e:
        print(f" ! LLM call failed ({e}) - falling back", file=sys.stderr)
        return fallback


# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------

def compute_streak(archive: list[dict], today: dt.date) -> int:
    """Consecutive days with an entry, counting back from today."""
    dates = {e["date"] for e in archive}
    dates.add(today.isoformat())
    streak, cursor = 0, today
    while cursor.isoformat() in dates:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return default


def main(dry_run: bool = False) -> int:
    today = dt.date.today()
    seen = set(load(SEEN_FILE, []))
    archive = load(ARCHIVE_FILE, [])

    print(f"lawtech-daily :: {today.isoformat()}")
    print(f"  {len(seen)} articles previously seen\n")

    # 1. Gather
    candidates: list[dict] = []
    for url in FEEDS:
        raw = fetch(url)
        if not raw:
            continue
        entries = parse_feed(raw)
        print(f"  + {len(entries):3d} items  {url[:58]}")
        for e in entries:
            if not e["title"] or not e["link"]:
                continue
            uid = uid_for(e["link"])
            if uid in seen:
                continue
            blob = f"{e['title']} {e['summary']}"
            # Headlines weigh double - higher signal than boilerplate summaries
            s = score_text(e["title"]) * 2 + score_text(e["summary"])
            if s < MIN_SCORE:
                continue
            e.update({"id": uid, "score": s, "tag": tag_article(blob)})
            candidates.append(e)

    # Dedup by id, keep highest score
    best: dict[str, dict] = {}
    for c in candidates:
        if c["id"] not in best or c["score"] > best[c["id"]]["score"]:
            best[c["id"]] = c
    ranked = sorted(best.values(), key=lambda c: -c["score"])[:CANDIDATE_POOL]

    print(f"\n  {len(ranked)} candidates above threshold {MIN_SCORE}")
    for c in ranked:
        print(f"    [{c['score']:3d}] {c['tag']:<14} {c['title'][:60]}")

    if not ranked:
        print("\n  nothing relevant today - leaving yesterday's entry in place")
        return 0

    pick = ranked[0]

    # 2. Summarise
    print(f"\n  picked: {pick['title'][:70]}")
    if dry_run:
        print("  (dry run - skipping LLM + writes)")
        return 0

    enriched = summarise(pick)

    entry = {
        "date":      today.isoformat(),
        "title":     pick["title"],
        "link":      pick["link"],
        "source":    pick.get("source", ""),
        "tag":       pick["tag"],
        "score":     pick["score"],
        "summary":   enriched["summary"],
        "why":       enriched["why"],
        "framework": enriched["framework"],
    }
    entry["streak"] = compute_streak(archive, today)

    # 3. Persist
    seen.add(pick["id"])
    archive = [a for a in archive if a["date"] != today.isoformat()] + [entry]
    archive.sort(key=lambda a: a["date"])

    TODAY_FILE.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    ARCHIVE_FILE.write_text(json.dumps(archive, indent=2, ensure_ascii=False))
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-SEEN_MEMORY:]))

    print(f"  tag={entry['tag']}  framework={entry['framework']}  streak={entry['streak']}")
    print("  wrote data/today.json, data/archive.json, data/seen.json")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and rank only; no LLM call, no writes")
    args = ap.parse_args()
    sys.exit(main(dry_run=args.dry_run))
