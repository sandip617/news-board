#!/usr/bin/env python3
"""Backup editor for Sandip's Board.

Runs from GitHub Actions after the daily Claude run. If today's edition
(data/days/DATE.json, India time) is already in the repo it does nothing.
Otherwise it collects the day's headlines from business RSS feeds
and market closes from Yahoo Finance, has Gemini write the edition from them,
updates data/index.json and data/terms.json, and emails subscribers via
MailerLite (once a day, skipped if a campaign for DATE already exists).

Env: GEMINI_API_KEY (required), MAILERLITE_API_KEY (optional, no email
without it), GEMINI_MODEL (optional), FORCE_DATE (optional, YYYY-MM-DD).
Only the Python standard library is used.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PUBLIC_URL = "https://news.itzsandippal.com/"
SENDER = "newsletter@itzsandippal.com"
SENDER_NAME = "Sandip's Board"


BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
BN_DAYS = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]


def log(*a):
    print("[backup]", *a, flush=True)


def http_json(url, data=None, headers=None, method=None, timeout=300):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:500]}
    except (urllib.error.URLError, TimeoutError, OSError) as e:  # timeout / network: let the caller move on
        return 0, {"error": f"{type(e).__name__}: {e}"}


def labels(day):
    bn = f"{day.day} {BN_MONTHS[day.month - 1]} {day.year}".translate(BN_DIGITS) + f", {BN_DAYS[day.weekday()]}"
    en = f"{day.strftime('%A')}, {day.day} {day.strftime('%B')} {day.year}"
    return bn, en


# ---------------------------------------------------------------- news & market (free sources)

FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Economic Times", "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"),
    ("Economic Times", "https://economictimes.indiatimes.com/news/company/rssfeeds/2143429.cms"),
    ("Mint", "https://www.livemint.com/rss/markets"),
    ("Mint", "https://www.livemint.com/rss/companies"),
    ("Mint", "https://www.livemint.com/rss/economy"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Business Standard", "https://www.business-standard.com/rss/economy-102.rss"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
    ("BBC", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/business/rss"),
]
UA = {"User-Agent": "Mozilla/5.0 (compatible; SandipsBoardBackup/1.0)"}


def http_text(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_html(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def collect_news(day):
    """Recent headlines (title, summary, link, time) from business RSS feeds,
    published in the 36 hours before the end of DAY (India time)."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    end = dt.datetime.combine(day, dt.time(23, 59), IST)
    start = end - dt.timedelta(hours=36) if day < dt.datetime.now(IST).date() else dt.datetime.now(IST) - dt.timedelta(hours=36)
    items, seen = [], set()
    for source, url in FEEDS:
        try:
            root = ET.fromstring(http_text(url).encode())
        except Exception as e:  # one broken feed must not stop the edition
            log(f"feed failed ({source}): {e}")
            continue
        for it in root.iter("item"):
            title = strip_html(it.findtext("title"))
            link = (it.findtext("link") or "").strip()
            if not title or not link.startswith("https://") or link in seen:
                continue
            try:
                when = parsedate_to_datetime(it.findtext("pubDate") or "")
                if when.tzinfo is None:
                    when = when.replace(tzinfo=dt.timezone.utc)
            except (TypeError, ValueError):
                continue
            if not (start <= when <= end):
                continue
            seen.add(link)
            items.append({"source": source, "title": title, "summary": strip_html(it.findtext("description"))[:280],
                          "url": link, "published": when.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")})
    items.sort(key=lambda x: x["published"], reverse=True)
    log(f"collected {len(items)} news items")
    return items[:60]


MARKETS = [  # name, Yahoo symbol, Bangla region, English region
    ("S&P 500", "^GSPC", "US", "US"), ("Dow Jones", "^DJI", "US", "US"), ("Nasdaq", "^IXIC", "US", "US"),
    ("Sensex", "^BSESN", "ভারত", "India"), ("Nifty 50", "^NSEI", "ভারত", "India"),
    ("Brent Crude", "BZ=F", "$ প্রতি ব্যারেল", "$ per barrel"), ("Gold", "GC=F", "$ প্রতি আউন্স", "$ per ounce"),
    ("USD/INR", "INR=X", "₹ প্রতি $", "₹ per $"),
]


def collect_market(day):
    """Latest closes up to DAY from Yahoo Finance's public chart data. A figure
    that can't be fetched is left out, never guessed."""
    end = dt.datetime.combine(day, dt.time(23, 59), IST).timestamp()
    bn, en, last_day = [], [], None
    for name, sym, reg_bn, reg_en in MARKETS:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?range=10d&interval=1d"
            res = json.loads(http_text(url))["chart"]["result"][0]
            pts = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None and t <= end]
            (t0, prev), (t1, close) = pts[-2], pts[-1]
        except Exception as e:
            log(f"market failed ({name}): {e}")
            continue
        pct = (close - prev) / prev * 100
        change = f"{pct:+.2f}%"
        direction = "up" if pct > 0.005 else "down" if pct < -0.005 else "flat"
        value = f"{close:,.2f}"
        bn.append({"name": name, "region": reg_bn, "value": value, "change": change, "dir": direction})
        en.append({"name": name, "region": reg_en, "value": value, "change": change, "dir": direction})
        d = dt.datetime.fromtimestamp(t1, IST).date()
        if name in ("S&P 500", "Sensex") and (last_day is None or d > last_day):
            last_day = d
    if not bn:
        return None, None
    last_day = last_day or day
    lb, le = labels(last_day)
    return ({"asOf": f"{lb}ের ক্লোজিং", "items": bn},
            {"asOf": f"Close of {le}", "items": en})


# ---------------------------------------------------------------- Gemini

def build_prompt(date, label_bn, label_en, template, used_terms, news):
    tpl = {k: v for k, v in template.items() if k not in ("caseStudy", "weekly", "market")}
    tpl["en"] = {k: v for k, v in template.get("en", {}).items() if k not in ("caseStudy", "weekly", "market")}
    return f"""You are the backup editor of "Sandip's Board", a bilingual (Bangla + English) daily business newspaper for BBA students in India.
Today (India time) is {date} ({label_en}).

Below are today's headlines collected from business news feeds (Economic Times, Mint, Business Standard, CNBC, BBC, The Guardian). From ONLY these items, pick the 7-8 most important GLOBAL business/economy stories a BBA student should know (M&A, central banks, inflation/GDP, oil/gold, big company results, startups/tech, Indian markets, policy/trade). Mix global and India; don't pick two items about the same story.

ACCURACY RULES (most important): use only facts and numbers that appear in the items below; never add facts, numbers or quotes from memory. If an item has few details, write a shorter summary rather than inventing. Each news item's source.url must be exactly the url of the item you used, and source.name its source.

WRITE: natural, simple standard Bangla (West Bengal style). Keep English business terms in English inside sentences, e.g. "সুদের হার (interest rate)". Use Western digits 0-9 inside text.
Fields:
- news: 7-8 items, most important first. Each {{id:"n1".., category (short Bangla), title, summary (2-5 sentences), why (1-2 sentences naming the BBA concept), source {{name,url}}}}.
- term: Term of the Day tied to today's news {{term, bangla, definition, example, formula ("" if none), tip}}. It must NOT be any of these already-used terms: {json.dumps(used_terms, ensure_ascii=False)}
- gd: {{topic, context, for:[3], against:[3]}}.
- blog: {{title, topic, readMin, body:[paragraph strings, "## " prefix = subheading], takeaways:[3]}}, 500-800 words; explain the concept from scratch (general textbook knowledge is fine here) and connect it to today's news.
- quiz: exactly 5 MCQs {{q, options:[4], answer (0-based), explain}} from today's news/blog/term; vary the answer position.
- en: full English version with the SAME structure, ids, numbers, URLs and quiz answer indexes: {{news, term (its "bangla" = short English gloss), gd, blog, quiz}}.

OUTPUT: only one JSON object, no markdown fences, no commentary, with keys news, term, gd, blog, quiz, en.
Schema example from yesterday's edition (copy field names exactly; do NOT copy its content):
{json.dumps(tpl, ensure_ascii=False)[:9000]}

TODAY'S NEWS ITEMS:
{json.dumps(news, ensure_ascii=False)}
"""


GAPI = "https://generativelanguage.googleapis.com/v1beta"
DEADLINE = time.time() + 45 * 60  # stay inside the Action's 60-minute limit
_models_cache = []


def version_of(name):
    m = re.search(r"(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def pick_models(key):
    """Flash models this key can use, best first: env GEMINI_MODEL, then
    newest non-lite Flash, then newest Flash Lite. Found from the API so a
    retired model name never breaks the backup."""
    if _models_cache:
        return _models_cache
    names = []
    code, res = http_json(f"{GAPI}/models?pageSize=200", None, {"x-goog-api-key": key}, timeout=60)
    if code == 200:
        for m in res.get("models", []):
            name = m.get("name", "").split("/")[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if "flash" not in name or re.search(r"image|tts|audio|live|embed|thinking-exp", name):
                continue
            names.append(name)
    else:
        log(f"could not list models (HTTP {code}), using fallbacks")
    names.sort(key=lambda n: ("lite" in n, "preview" in n or "exp" in n, -version_of(n), len(n)))
    env_model = os.environ.get("GEMINI_MODEL", "").strip()
    order = ([env_model] if env_model else []) + names + ["gemini-flash-latest", "gemini-flash-lite-latest"]
    seen = set()
    _models_cache.extend(m for m in order if not (m in seen or seen.add(m)))
    log("models to try:", ", ".join(_models_cache[:6]))
    return _models_cache


def call_gemini(prompt, key):
    last = "no model tried"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 60000},
    }
    for model in pick_models(key)[:4]:
        if time.time() > DEADLINE:
            last += " (stopped: out of time)"
            break
        for attempt in range(2):  # one retry per model, then move on
            code, res = http_json(f"{GAPI}/models/{model}:generateContent", payload, {"x-goog-api-key": key}, timeout=480)
            if code == 200:
                parts = (res.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                if text.strip():
                    return model, text
                last = f"{model}: empty answer ({json.dumps(res)[:300]})"
                break
            last = f"{model}: HTTP {code} {json.dumps(res)[:200]}"
            log("failed:", last)
            if code not in (429, 500, 502, 503, 504) or attempt == 1 or time.time() > DEADLINE:
                break
            time.sleep(65 if code == 429 else 15)  # free tier counts requests per minute
    raise RuntimeError("Gemini failed: " + last)


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in answer")
    return json.loads(text[start:end + 1])


def validate(ed, used_terms, urls):
    errs = []
    for side, d in (("bn", ed), ("en", ed.get("en") or {})):
        news = d.get("news") or []
        if not 5 <= len(news) <= 8:
            errs.append(f"{side}: {len(news)} news")
        for n in news:
            if (n.get("source") or {}).get("url", "") not in urls:
                errs.append(f"{side}: news {n.get('id')} source url is not one of the given items")
        quiz = d.get("quiz") or []
        if len(quiz) != 5 or any(q.get("answer") not in (0, 1, 2, 3) or len(q.get("options") or []) != 4 for q in quiz):
            errs.append(f"{side}: quiz must be 5 items with 4 options and answer 0-3")
        for k in ("term", "gd", "blog"):
            if not d.get(k):
                errs.append(f"{side}: missing {k}")
    if not errs:
        if [n.get("id") for n in ed["news"]] != [n.get("id") for n in ed["en"]["news"]]:
            errs.append("bn/en news ids differ")
        ed["en"]["quiz"] = [dict(q, answer=b["answer"]) for q, b in zip(ed["en"]["quiz"], ed["quiz"])]
        if str(ed["term"].get("term", "")).strip().lower() in {t.lower() for t in used_terms}:
            errs.append("term already used")
    return errs


# ---------------------------------------------------------------- MailerLite

ML = "https://connect.mailerlite.com/api"


def ml(path, key, data=None, method=None):
    return http_json(ML + path, data, {"Authorization": f"Bearer {key}"}, method, timeout=60)


def campaign_exists(name, key):
    for status in ("sent", "ready", "draft"):
        code, res = ml(f"/campaigns?filter[status]={status}&limit=50", key)
        if code != 200:
            raise RuntimeError(f"MailerLite list campaigns HTTP {code}: {res}")
        if any(c.get("name") == name for c in res.get("data", [])):
            return True
    return False


def email_html(ed, date):
    e = html.escape
    lead = ed["news"][0]
    summary = " ".join(re.split(r"(?<=[।.!?])\s+", lead["summary"])[:2])
    more = "".join(f'<li style="margin:0 0 8px">{e(n["title"])}</li>' for n in ed["news"][1:4])
    t = ed["term"]
    link = f"{PUBLIC_URL}#{date}"
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#f5f1e8">
<div style="max-width:600px;margin:0 auto;padding:24px 18px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1b1814;background:#f5f1e8">
<p style="margin:0;color:#b0241c;font-size:13px">{e(ed["dateLabel"])}</p>
<h1 style="margin:4px 0 18px;font-size:28px;border-bottom:3px solid #1b1814;padding-bottom:8px">Sandip's Board</h1>
<h2 style="margin:0 0 8px;font-size:21px;line-height:1.35">{e(lead["title"])}</h2>
<p style="margin:0 0 18px;line-height:1.6">{e(summary)}</p>
<ul style="padding-left:18px;line-height:1.5;margin:0 0 18px">{more}</ul>
<p style="margin:0 0 22px;padding:10px 12px;border-left:4px solid #b0241c;background:#fff">আজকের শব্দ: <b>{e(t["term"])}</b> — {e(t["bangla"])}</p>
<p style="text-align:center;margin:0 0 26px"><a href="{e(link)}" style="display:inline-block;background:#b0241c;color:#fff;text-decoration:none;padding:13px 26px;border-radius:6px;font-weight:bold">পুরো সংস্করণ পড়ো</a></p>
<p style="font-size:12px;color:#6b645a;text-align:center;margin:0">Sandip's Board · বিনিয়োগের পরামর্শ নয় · <a href="{{$unsubscribe}}" style="color:#6b645a">আনসাবস্ক্রাইব</a></p>
</div></body></html>"""


def send_email(ed, date, key):
    name = f"Sandip's Board – {date}"
    if campaign_exists(name, key):
        log("email already sent today, skipping")
        return "already sent"
    code, res = ml("/groups?limit=100", key)
    if code != 200:
        raise RuntimeError(f"MailerLite groups HTTP {code}: {res}")
    groups = [g["id"] for g in res.get("data", []) if not re.search(r"test|demo", g.get("name", ""), re.I)]
    if not groups:
        raise RuntimeError("no MailerLite groups to send to")
    subject = f"আজকের Sandip's Board: {ed['news'][0]['title']}"
    if len(subject) > 90:
        subject = subject[:87].rstrip() + "…"
    code, res = ml("/campaigns", key, {
        "name": name, "type": "regular", "groups": groups,
        "emails": [{"subject": subject, "from_name": SENDER_NAME, "from": SENDER,
                    "content": email_html(ed, date)}],
    })
    if code not in (200, 201):
        raise RuntimeError(f"MailerLite create campaign HTTP {code}: {res}")
    cid = res["data"]["id"]
    code, res = ml(f"/campaigns/{cid}/schedule", key, {"delivery": "instant"})
    if code not in (200, 201):
        raise RuntimeError(f"MailerLite schedule HTTP {code}: {res}")
    return "sent"


# ---------------------------------------------------------------- main

def main():
    day = dt.date.fromisoformat(os.environ["FORCE_DATE"]) if os.environ.get("FORCE_DATE") else dt.datetime.now(IST).date()
    date = day.isoformat()
    day_file = DATA / "days" / f"{date}.json"
    if day_file.exists():
        log(f"{date} already published (Claude did it). Nothing to do.")
        return 0

    gkey = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gkey:
        log("ERROR: GEMINI_API_KEY secret is missing")
        return 1

    index = json.loads((DATA / "index.json").read_text())
    terms = json.loads((DATA / "terms.json").read_text())
    template = json.loads((DATA / "days" / f"{index['latest']}.json").read_text())
    used_terms = [t["term"] for t in terms["terms"]]
    label_bn, label_en = labels(day)
    news = collect_news(day)
    if len(news) < 7:
        log(f"ERROR: only {len(news)} news items found in the feeds, not enough for an edition")
        return 1
    urls = {n["url"] for n in news}
    market_bn, market_en = collect_market(day)
    prompt = build_prompt(date, label_bn, label_en, template, used_terms, news)

    ed, problems = None, []
    for attempt in range(3):
        if time.time() > DEADLINE:
            break
        try:
            model, text = call_gemini(prompt + ("\n\nYour previous answer had problems: " + "; ".join(problems) if problems else ""), gkey)
            cand = parse_json(text)
            problems = validate(cand, used_terms, urls)
            if not problems:
                ed = cand
                log("edition written by", model)
                break
            log("invalid edition:", problems)
        except RuntimeError as e:  # every model failed this round
            problems = []
            log("round failed:", e)
        except (ValueError, KeyError, TypeError) as e:
            problems = [f"answer was not valid JSON ({e})"]
            log("bad answer:", e)
    if ed is None:
        log("ERROR: could not get a valid edition from Gemini:", problems)
        return 1

    # fill the fixed fields ourselves
    ed = {"date": date, "dateLabel": label_bn, "edition": 1,
          "updatedAt": dt.datetime.now(IST).replace(microsecond=0).isoformat(),
          "generatedBy": "gemini-backup", **{k: v for k, v in ed.items() if k not in ("date", "dateLabel", "edition", "updatedAt")}}
    ed["en"]["dateLabel"] = label_en
    if market_bn:
        ed["market"], ed["en"]["market"] = market_bn, market_en
    else:  # no live prices: keep the last known ones, clearly dated by their asOf
        ed["market"], ed["en"]["market"] = template["market"], template["en"]["market"]
    if template.get("caseStudy"):
        ed["caseStudy"] = template["caseStudy"]
        if template.get("en", {}).get("caseStudy"):
            ed["en"]["caseStudy"] = template["en"]["caseStudy"]
    for key in ("news", "market", "term", "gd", "blog", "quiz"):  # keep key order like Claude's files
        ed[key] = ed.pop(key)
    for key in ("news", "market", "term", "gd", "blog", "quiz"):
        ed["en"][key] = ed["en"].pop(key)
    en = ed.pop("en")
    ed["en"] = en

    day_file.write_text(json.dumps(ed, ensure_ascii=False, indent=1) + "\n")
    index["days"] = [d for d in index["days"] if d.get("date") != date]
    index["days"].insert(0, {"date": date, "label": label_bn, "labelEn": label_en,
                             "headline": ed["news"][0]["title"], "headlineEn": ed["en"]["news"][0]["title"]})
    index["days"].sort(key=lambda d: d["date"], reverse=True)
    index["latest"] = index["days"][0]["date"]
    (DATA / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    t, te = ed["term"], ed["en"]["term"]
    fields = ("term", "bangla", "definition", "example", "formula", "tip")
    terms["terms"].insert(0, {"date": date, **{f: t.get(f, "") for f in fields}, "en": {f: te.get(f, "") for f in fields}})
    (DATA / "terms.json").write_text(json.dumps(terms, ensure_ascii=False, indent=1) + "\n")
    log(f"wrote {day_file.name}, index.json, terms.json")

    mkey = os.environ.get("MAILERLITE_API_KEY", "").strip()
    if not mkey:
        log("ERROR: MAILERLITE_API_KEY secret is missing, edition saved but NO email sent")
        return 2
    try:
        log("email:", send_email(ed, date, mkey))
    except RuntimeError as e:
        log("ERROR: edition saved but email failed:", e)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
