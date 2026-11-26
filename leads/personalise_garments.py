"""Write a short personal opening line for each garments contact with Gemini, ahead of sending.

usage: GEMINI_API_KEY=... python3 -I leads/personalise_garments.py

Reads emails.txt (the garments queue) and the facts about each company in the master's "Master Contacts" sheet,
and writes garments_openers.csv (email, company, facts, opener, status). Review or edit that file before sending:
send_campaign.py uses an opener only when its status is "ok" and it isn't blank; every other contact gets the
normal template. Safe to stop and rerun: finished companies are skipped, and failed ones are retried.
Only public company facts are sent to Gemini, never email addresses.
"""
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from openpyxl import load_workbook

proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(proj, "garments_openers.csv")
# Tried in order. The "-latest" aliases follow Google's current Flash models, so a retired model doesn't break the run;
# each model has its own free quota, so when one is busy, retired or out of quota the next one takes over.
MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_MODEL", "gemini-flash-latest,gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-2.5-flash-lite").split(",") if m.strip()]
RETRIES, RETRY_WAIT = 3, 15  # for "high demand" (503) and server errors: wait 15s, 30s, 45s before giving up on a model
PACE_SECONDS = float(os.environ.get("GEMINI_PACE_SECONDS", "6"))  # about 10 requests a minute, under free-tier limits
# With only one fact (usually just "member of X association") the opener comes out generic, so those keep the template
MIN_FACTS = int(os.environ.get("GEMINI_MIN_FACTS", "2"))
FIELDS = ["email", "company", "facts", "opener", "status"]

# Where we found a company says something true about it
SOURCE_FACTS = [
    ("phma", "member of the Pakistan Hosiery Manufacturers & Exporters Association (PHMA), so a hosiery/knitwear maker"),
    ("associations.csv", "member of the Pakistan Hosiery Manufacturers & Exporters Association (PHMA), so a hosiery/knitwear maker"),
    ("pcfa", "member of the Pakistan Cotton Fashion Apparel Manufacturers & Exporters Association (PCFA)"),
    ("prgmea", "member of the Pakistan Readymade Garments Manufacturers & Exporters Association (PRGMEA)"),
    ("heimtextil", "exhibitor at Heimtextil Frankfurt, the home textiles trade fair"),
    ("denim", "listed in TDAP's denim exporters brochure"),
    ("tdap_chambers", "listed by TDAP as a Karachi garment exporter"),
    ("ch6162", "listed in TDAP's directory of Karachi apparel exporters"),
    ("landhi", "member of the Landhi Association of Trade & Industry, textiles section"),
    ("industrial_areas", "member of the Landhi Association of Trade & Industry, textiles section"),
    ("home_associations", "Karachi textile mill listed by APTMA / the Pakistan Bedwear Exporters Association"),
    ("fairs.csv", "exhibitor at an international apparel trade fair"),
]

PROMPT = """You are Bilal Shaikh, Director of Mehran Prints, a textile screen printing company in Karachi, located at
Sector 16B, Federal B Area (North Karachi Industrial Area). If the company is in Federal B Area or North Karachi you
may mention that we are close by; otherwise don't mention location.
Write ONE short opening paragraph (1-2 sentences, at most 40 words) for a formal B2B introduction email to the
company below. It goes right after "Greetings from Mehran Prints!" and before a standard paragraph introducing
Mehran Prints, so do not introduce Mehran Prints, do not greet, and do not sign off.
Say plainly why we are writing to them specifically, using ONLY the facts given, and connect it to garment/textile
printing. This is our FIRST contact with them, so:
- do not claim we know, admire, have followed or are acquainted with them;
- do not call us fellow members of any association (we are not members);
- no flattery or superlatives (distinguished, esteemed, prominent, renowned, leading, reputed);
- do not invent products, buyers, brands, numbers, awards or history that are not in the facts.
No links, no email addresses, no exclamation marks. Formal, respectful Pakistani business English.
Reply with the paragraph text only.

Company: {company}
Facts:
{facts}"""


class QuotaExceeded(Exception):
    pass


def facts_for(row):
    facts = []
    industry = str(row.get("Industry / Product Focus") or "").strip()
    if industry and "towel" not in industry.lower():
        facts.append(f"Product focus: {industry}")
    place = str(row.get("Address / City") or "").strip()
    if place and place.lower() not in ("karachi", "karachi, pakistan"):
        facts.append(f"Located at: {place}")
    sources = str(row.get("Sources") or "").lower()
    for key, fact in SOURCE_FACTS:
        if key in sources and fact not in facts:
            facts.append(fact)
    return facts


dead_models = set()  # retired or out of quota for the rest of this run


def call_model(model, body, key):
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    try:
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"no text in reply: {json.dumps(data)[:200]}")


def ask_gemini(company, facts, key):
    body = {"contents": [{"parts": [{"text": PROMPT.format(company=company, facts="\n".join(f"- {f}" for f in facts))}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400}}
    last = "no model available"
    for model in [m for m in MODELS if m not in dead_models]:
        for attempt in range(RETRIES + 1):
            try:
                return call_model(model, body, key)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                last = f"{model}: HTTP {e.code}: {detail[:160]}"
                if e.code == 429 or "RESOURCE_EXHAUSTED" in detail or e.code == 404:
                    print(f"  {model} {'out of quota' if e.code != 404 else 'not available'}; switching model")
                    dead_models.add(model)
                    break
                if e.code in (500, 502, 503, 504) and attempt < RETRIES:
                    time.sleep(RETRY_WAIT * (attempt + 1))  # busy: wait and try again
                    continue
                break  # still failing, or a request error: try the next model
            except (urllib.error.URLError, TimeoutError) as e:
                last = f"{model}: {e}"
                if attempt < RETRIES:
                    time.sleep(RETRY_WAIT * (attempt + 1))
                    continue
                break
    if all(m in dead_models for m in MODELS):
        raise QuotaExceeded(last)
    raise RuntimeError(last)


def check(opener, facts):
    """Reason the opener can't be used, or None if it's fine."""
    words = opener.split()
    if not 8 <= len(words) <= 50:
        return f"bad length ({len(words)} words)"
    # First contact: no claimed familiarity, no association membership we don't have, no unbacked praise
    claim = re.search(r"\b(admir\w*|acquaint\w*|long known|have followed|fellow|distinguished|esteemed|prominent|"
                      r"renowned|leading|reputed|well[- ]known)\b", opener, re.I)
    if claim:
        return f"claims or flattery ({claim.group(0)})"
    # "We are close by" is only true for companies in FB Area / North Karachi, where Mehran Prints is
    if re.search(r"\b(close by|close to (us|our)|closely located|near(by)? (us|our|to us)|nearby|neighbou?r\w*|next door|"
                 r"vicinity|proximity|in our area|same area)\b", opener, re.I) and \
            not re.search(r"federal b|f\.?\s?b\.? area|north karachi|sector 16", " ".join(facts), re.I):
        return "says we are close by, but the company isn't in FB Area / North Karachi"
    if "\n" in opener.strip():
        return "more than one paragraph"
    if re.search(r"https?://|www\.|@", opener):
        return "contains a link or email"
    if re.search(r"\b(dear|greetings|regards|sincerely)\b", opener, re.I) or "!" in opener:
        return "greeting, sign-off or exclamation"
    digits = set(re.findall(r"\d+", opener)) - set(re.findall(r"\d+", " ".join(facts)))
    if digits:
        return f"numbers not in the facts ({', '.join(sorted(digits))})"
    return None


def save(rows):
    with open(OUT + ".tmp", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows.values())
    os.replace(OUT + ".tmp", OUT)


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("Set GEMINI_API_KEY first (free key from Google AI Studio). Without it every contact just gets the template.")
    if re.search(r"\s", key) or "paste-your-key" in key or len(key) < 20:
        sys.exit("GEMINI_API_KEY doesn't look like a key (it has spaces/line breaks or placeholder text). "
                 "Fix the export line in ~/.bashrc so it holds only the key, then open a new terminal.")
    master = max(glob.glob(os.path.join(proj, "karachi_textile_garment_master_database_v*.xlsx")),
                 key=lambda p: int(re.search(r"_v(\d+)\.xlsx$", p).group(1)))
    ws = load_workbook(master, read_only=True)["Master Contacts"]
    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter)
    info = {r[1]: dict(zip(header, r)) for r in rows_iter if r and r[1]}

    queue = [l.strip().lower() for l in open(os.path.join(proj, "emails.txt")) if l.strip()]
    rows = {}
    if os.path.exists(OUT):
        rows = {r["email"]: r for r in csv.DictReader(open(OUT, newline=""))}
    done_by_company = {r["company"]: r for r in rows.values() if r["status"] == "ok" and r["company"]}

    made = fallback = 0
    for email in queue:
        old = rows.get(email)
        if old and (old["status"] == "ok" or old["status"].startswith("template: not enough data")):
            continue  # finished earlier; edits you made to the file are kept
        r = info.get(email, {})
        company = str(r.get("Company") or "").strip()
        facts = facts_for(r)
        row = {"email": email, "company": company, "facts": " | ".join(facts), "opener": "", "status": ""}
        if not company or len(facts) < MIN_FACTS:
            row["status"] = "template: not enough data"
        elif company in done_by_company:  # same company, other address: reuse, no extra request
            row.update(opener=done_by_company[company]["opener"], status="ok")
        else:
            try:
                opener = ask_gemini(company, facts, key)
                problem = check(opener, facts)
                # A rejected opener is kept for review only; the campaign uses an opener just when status is "ok"
                row.update(opener=opener, status="ok" if not problem else f"template: {problem}")
            except QuotaExceeded as e:
                save(rows)
                print(f"No Gemini model left (quota used up or retired); stopped. {made} openers written this run. "
                      f"Rerun later to continue; everyone not done gets the template meanwhile. ({e})")
                return
            except (RuntimeError, urllib.error.URLError, TimeoutError) as e:
                row["status"] = f"template: Gemini error, will retry ({str(e)[:120]})"
            time.sleep(PACE_SECONDS)
        rows[email] = row
        if row["status"] == "ok":
            made += 1
            done_by_company[company] = row
        else:
            fallback += 1
        save(rows)
        print(f"{email}: {row['status']}")

    ok = sum(r["status"] == "ok" for r in rows.values())
    print(f"done: {made} new openers, {fallback} on the template this run | {ok} of {len(queue)} queued contacts personalised")


if __name__ == "__main__":
    main()
